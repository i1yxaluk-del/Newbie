<#
.SYNOPSIS
    Автоматическое развёртывание МСП Облако в Yandex Cloud.
    Теперь с правильным выводом ошибок и уникальными именами ресурсов.

.УРОКИ ДЕПЛОЯ (читай перед изменением скрипта):
  - Домен: БУКВЫ ДОЛЖНЫ СОВПАДАТЬ С DNS! У нас была опечатка
    mcp-claude.online вместо msp-claude.online → Caddy получил
    staging-сертификаты LE, браузеры их не приняли, потрачено 2 часа.
  - Static IP: preemptible-ВМ получает НОВЫЙ IP при каждом рестарте.
    Резервируем static IP (189.73₽/мес) и привязываем к ВМ через
    add-one-to-one-nat — так DNS A-записи не устаревают.
  - UserKnownHostsFile=NUL: preemptible-ВМ меняет host keys при рестарте.
    Без этого SSH на Win10/OpenSSH ломается с REMOTE HOST IDENTIFICATION HAS CHANGED.
  - yc через cmd /c: PowerShell 5.1 не может корректно обработать
    stderr от yc (пишет ErrorRecord). Команда `cmd /c "yc ... 2>&1"`
    сливает stderr в stdout, и PS видит чистый текст.
  - SCP через VPN (AmneziaWG): ненадёжно (таймауты). Используйте
    echo BASE64 | base64 -d > file через SSH для маленьких файлов,
    или архив zip через scp без WireGuard.
  - OAuth-токены после 01.06.2026 НЕ работают с yc CLI (IAM token exchange).
    УРОК МИГРАЦИИ 2: используйте сервисный аккаунт —
    yc config set service-account-key <path-to-authorized_key.json>.
    Если профиль уже настроен на SA — скрипт работает без изменений.
#>

[CmdletBinding()]
param(
    # ВАЖНО: дефолт домена ТОЧНО совпадает с DNS A-записью!
    # Была опечатка mcp-claude.online → NXDOMAIN для LE.
    [string]$Domain = "msp-claude.online",
    [string]$Zone = "ru-central1-a",
    [string]$VmName = "msp-cloud-vm",
    [int]$VmCores = 2,
    [int]$VmMemoryGb = 4,
    [int]$VmDiskGb = 50,
    [bool]$Preemptible = $true,
    # Резервировать static IP? (+189.73₽/мес, но IP переживает рестарт ВМ)
    [bool]$UseStaticIp = $true,
    [switch]$Recreate,
    [switch]$SkipMail
)

$ErrorActionPreference = "Stop"
$env:YC_CLI_INITIALIZATION_SILENCE = "true"   # убираем предупреждение yc

# Фикс UTF-8 для консоли (безопасно)
$script:__PrevOutputEncoding = $OutputEncoding
$script:__PrevConsoleOutputEncoding = $null
try { $script:__PrevConsoleOutputEncoding = [Console]::OutputEncoding } catch { }
try { $OutputEncoding = [System.Text.UTF8Encoding]::new($false) } catch { }
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

try {
    $RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
    $DeployDir = $PSScriptRoot
    $StateFile = Join-Path $DeployDir ".deploy-state.json"
    $LogFile = Join-Path $env:TEMP ("msp-deploy-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
    $SshKeyPath = Join-Path $env:USERPROFILE ".ssh\id_ed25519_yc_new"
    $SshKeyPubPath = "$SshKeyPath.pub"

    # Полный путь к ssh.exe — PowerShell 5.1 может не иметь его в PATH.
    # Проверяем System32\OpenSSH первым, затем PATH.
    $SshExe = $null
    $sysSsh = "C:\Windows\System32\OpenSSH\ssh.exe"
    if (Test-Path $sysSsh) { $SshExe = $sysSsh }
    elseif (Get-Command ssh -ErrorAction SilentlyContinue) { $SshExe = (Get-Command ssh).Source }
    else { Write-Fail "ssh.exe не найден. Установите OpenSSH Client."; exit 1 }

    # Общие SSH-опции для preemptible ВМ:
    #   UserKnownHostsFile=NUL — не сохранять host keys (ВМ меняет их при рестарте)
    #   StrictHostKeyChecking=no — не спрашивать подтверждение
    $SshOpts = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL"

    # ═══════════════════════════════════════════════════════════════════
    # Функция безопасного вызова yc с выводом реальной ошибки
    # ═══════════════════════════════════════════════════════════════════
    function Invoke-Yc {
        param(
            [Parameter(ValueFromRemainingArguments=$true)]
            [string[]]$Arguments
        )
        $cmdLine = "yc " + ($Arguments -join " ")
        Write-Debug "EXEC: $cmdLine"
        # Выполняем через cmd /c, перенаправляя stderr в stdout (2>&1)
        $output = cmd /c "$cmdLine 2>&1"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "`n❌ Ошибка при выполнении yc команды:" -ForegroundColor Red
            Write-Host $output -ForegroundColor Red
            throw "yc command failed with exit code ${LASTEXITCODE}: $cmdLine"
        }
        return $output
    }

    # Вспомогательные функции вывода
    function Write-Stage { param([int]$Num, [int]$Total, [string]$Text)
        Write-Host ""
        Write-Host ("═══ [{0}/{1}] {2} ═══" -f $Num, $Total, $Text) -ForegroundColor Cyan
        Add-Content -Path $LogFile -Value ("[{0}] STAGE {1}/{2}: {3}" -f (Get-Date -Format "HH:mm:ss"), $Num, $Total, $Text)
    }
    function Write-Info { param([string]$Text) Write-Host "  $Text" -ForegroundColor Gray; Add-Content -Path $LogFile -Value "  $Text" }
    function Write-Ok   { param([string]$Text) Write-Host "  ✓ $Text" -ForegroundColor Green; Add-Content -Path $LogFile -Value "  OK: $Text" }
    function Write-Warn { param([string]$Text) Write-Host "  ! $Text" -ForegroundColor Yellow; Add-Content -Path $LogFile -Value "  WARN: $Text" }
    function Write-Fail { param([string]$Text) Write-Host "  ✗ $Text" -ForegroundColor Red; Add-Content -Path $LogFile -Value "  FAIL: $Text" }

    function Format-BoxField {
        param([string]$Value, [int]$Width = 52)
        if ($null -eq $Value) { $Value = "" }
        if ($Value.Length -gt $Width) {
            if ($Width -le 3) { return $Value.Substring($Value.Length - $Width) }
            return "..." + $Value.Substring($Value.Length - $Width + 3)
        }
        return $Value.PadRight($Width)
    }

    function Save-State { param([hashtable]$State) $State | ConvertTo-Json -Depth 5 | Out-File -FilePath $StateFile -Encoding utf8 }
    function Load-State { if (Test-Path $StateFile) { return Get-Content -Path $StateFile -Raw | ConvertFrom-Json } else { return $null } }

    # ═══════════════════════════════════════════════════════════════════
    # Заголовок
    # ═══════════════════════════════════════════════════════════════════
    Clear-Host
    Write-Host @"
`
  +--------------------------------------------------------------+
  |   MSP Cloud - auto-deploy to Yandex Cloud                    |
  +--------------------------------------------------------------+
  |                                                                |
  |   Domain:    $(Format-BoxField $Domain)|
  |   Zone:      $(Format-BoxField $Zone)|
  |   VM:        $(Format-BoxField "$VmName ($VmCores vCPU / $VmMemoryGb GB / $VmDiskGb GB SSD)")|
  |   Type:      $(Format-BoxField $(if($Preemptible){"preemptible (cheaper)"}else{"guaranteed"}))|
  |   Static IP: $(Format-BoxField $(if($UseStaticIp){"YES (+189.73 RUR/mo, survives VM restart)"}else{"NO (IP changes on restart)"}))|
  |   Mail:      $(Format-BoxField $(if($SkipMail){"skipped"}else{"Stalwart (admin@/sales@/alert@)"}))|
  |                                                                |
  |   Log:       $(Format-BoxField $LogFile)|
  |                                                                |
  +--------------------------------------------------------------+
`@ -ForegroundColor Cyan

    # ═══════════════════════════════════════════════════════════════════
    # Стадия 1: yc CLI + SSH client
    # ═══════════════════════════════════════════════════════════════════
    Write-Stage 1 8 "Проверка yc CLI и SSH"

    # yc CLI установка
    $ycCmd = Get-Command yc -ErrorAction SilentlyContinue
    if (-not $ycCmd) {
        Write-Info "yc CLI не найден, устанавливаю..."
        $ycInstaller = Join-Path $env:TEMP "yc-install.ps1"
        try {
            Invoke-WebRequest -Uri "https://storage.yandexcloud.net/yandexcloud-yc/install.ps1" -OutFile $ycInstaller -UseBasicParsing
            & powershell -ExecutionPolicy Bypass -File $ycInstaller -n
            $env:Path += ";$env:USERPROFILE\yandex-cloud\bin"
            $ycCmd = Get-Command yc -ErrorAction SilentlyContinue
            if (-not $ycCmd) { throw "yc CLI not found after installation" }
            Write-Ok "yc CLI установлен"
        } catch {
            Write-Fail "Не удалось установить yc CLI: $_"
            exit 1
        }
    } else {
        $ver = Invoke-Yc version | Select-Object -First 1
        Write-Ok "yc CLI: $ver"
    }

    # SSH client (проверка без вызова ssh -V, чтобы избежать ложных ошибок)
    # ВАЖНО: на Windows 10 ssh.exe может быть в System32\OpenSSH, но не в PATH.
    # Мы уже нашли $SshExe выше.
    $scpPath = Get-Command scp -ErrorAction SilentlyContinue
    if (-not $scpPath) {
        $sysScp = "C:\Windows\System32\OpenSSH\scp.exe"
        if (Test-Path $sysScp) {
            $env:Path += ";C:\Windows\System32\OpenSSH"
            $scpPath = Get-Command scp -ErrorAction SilentlyContinue
        }
    }
    Write-Ok "SSH client: $SshExe"
    if (-not $scpPath) { Write-Warn "SCP client не найден — файлы будут загружаться через base64+SSH" }
    else { Write-Ok "SCP client: $($scpPath.Source)" }

    # ═══════════════════════════════════════════════════════════════════
    # Стадия 2: Авторизация и создание уникального каталога
    # ═══════════════════════════════════════════════════════════════════
    Write-Stage 2 8 "Авторизация в Yandex Cloud и подготовка каталога"

    # Проверяем/создаём профиль yc
    $ycProfile = Invoke-Yc config list
    $ycProfileStr = $ycProfile -join "`n"
    if ($ycProfileStr -notmatch "token:") {
        Write-Info "Нет активного yc-профиля. Открываю браузер для OAuth..."
        $oauthUrl = "https://oauth.yandex.com/authorize?response_type=token&client_id=1a6990aa636648e9b2ef855fa7bec2fb"
        Start-Process $oauthUrl
        Write-Host ""
        Write-Host "  В браузере:" -ForegroundColor Yellow
        Write-Host "    1. Нажмите 'Разрешить'" -ForegroundColor Yellow
        Write-Host "    2. Скопируйте OAuth-токен из адресной строки" -ForegroundColor Yellow
        Write-Host ""
        $token = Read-Host -Prompt "  Вставьте OAuth-токен"
        if ([string]::IsNullOrWhiteSpace($token)) { Write-Fail "Пустой токен"; exit 1 }
        Invoke-Yc config profile create msp-cloud | Out-Null
        Invoke-Yc config profile activate msp-cloud | Out-Null
        Invoke-Yc config set token $token | Out-Null
        Write-Ok "Профиль 'msp-cloud' создан"
    } else {
        Write-Ok "yc-профиль активен"
    }

    # Получаем облако
    $cloudsJson = Invoke-Yc resource-manager cloud list --format json
    $clouds = $cloudsJson | ConvertFrom-Json
    if (-not $clouds -or $clouds.Count -eq 0) {
        Write-Fail "Нет облака. Создайте вручную в https://console.cloud.yandex.ru/"
        exit 1
    }
    $cloudId = $clouds[0].id
    Invoke-Yc config set cloud-id $cloudId | Out-Null
    Write-Info "Cloud: $($clouds[0].name) ($cloudId)"

    # --- Уникальное имя каталога ---
    $state = Load-State
    if ($state -and $state.folderName -and -not $Recreate) {
        $folderName = $state.folderName
        Write-Info "Использую существующий каталог из state: $folderName"
    } else {
        $folderName = "msp-cloud-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Write-Info "Будет создан новый каталог: $folderName"
    }

    # Проверяем, существует ли уже каталог с таким именем
    $foldersJson = Invoke-Yc resource-manager folder list --cloud-id $cloudId --format json
    $folders = $foldersJson | ConvertFrom-Json
    $folder = $folders | Where-Object { $_.name -eq $folderName } | Select-Object -First 1

    if (-not $folder) {
        Write-Info "Создаю каталог '$folderName'..."
        Invoke-Yc resource-manager folder create --name $folderName --cloud-id $cloudId | Out-Null
        $folderJson = Invoke-Yc resource-manager folder get --name $folderName --cloud-id $cloudId --format json
        $folder = $folderJson | ConvertFrom-Json
        Write-Ok "Каталог создан: $folderName ($($folder.id))"
    } else {
        Write-Ok "Каталог уже существует: $folderName ($($folder.id))"
    }
    $folderId = $folder.id
    Invoke-Yc config set folder-id $folderId | Out-Null
    Invoke-Yc config set compute-default-zone $Zone | Out-Null

    # ═══════════════════════════════════════════════════════════════════
    # Стадия 3: SSH ключ + VPC + Subnet + Security Group (уникальные имена)
    # ═══════════════════════════════════════════════════════════════════
    Write-Stage 3 8 "SSH ключ + сеть"

    # SSH ключ
    if (-not (Test-Path $SshKeyPath)) {
        Write-Info "Генерирую SSH-ключ ed25519..."
        $sshDir = Split-Path $SshKeyPath -Parent
        if (-not (Test-Path $sshDir)) { New-Item -ItemType Directory -Path $sshDir | Out-Null }
        & ssh-keygen -t ed25519 -f $SshKeyPath -N '""' -C "msp-yc-deploy" 2>&1 | Out-Null
        Write-Ok "SSH ключ создан"
    } else {
        Write-Ok "SSH ключ существует"
    }
    $sshPubKey = (Get-Content -Path $SshKeyPubPath -Raw).Trim()

    # Уникальные имена для сети и подсети (привязываем к имени каталога, чтобы не пересекались)
    $netName = "msp-net-${folderName}"
    $subnetName = "msp-subnet-${folderName}"
    $sgName = "msp-sg-${folderName}"

    # VPC
    $networksJson = Invoke-Yc vpc network list --folder-id $folderId --format json
    $networks = $networksJson | ConvertFrom-Json
    $net = $networks | Where-Object { $_.name -eq $netName } | Select-Object -First 1
    if (-not $net) {
        Write-Info "Создаю VPC '$netName'..."
        Invoke-Yc vpc network create --name $netName --folder-id $folderId | Out-Null
        $netJson = Invoke-Yc vpc network get --name $netName --folder-id $folderId --format json
        $net = $netJson | ConvertFrom-Json
        Write-Ok "VPC создана: $netName ($($net.id))"
    } else {
        Write-Ok "VPC уже существует: $netName ($($net.id))"
    }

    # Subnet
    $subnetsJson = Invoke-Yc vpc subnet list --folder-id $folderId --format json
    $subnets = $subnetsJson | ConvertFrom-Json
    $subnet = $subnets | Where-Object { $_.name -eq $subnetName -and $_.zone_id -eq $Zone } | Select-Object -First 1
    if (-not $subnet) {
        Write-Info "Создаю subnet '$subnetName' в $Zone..."
        Invoke-Yc vpc subnet create --name $subnetName --network-id $net.id --zone $Zone --range 10.10.0.0/24 --folder-id $folderId | Out-Null
        $subnetJson = Invoke-Yc vpc subnet get --name $subnetName --folder-id $folderId --format json
        $subnet = $subnetJson | ConvertFrom-Json
        Write-Ok "Subnet создана: $subnetName ($($subnet.id))"
    } else {
        Write-Ok "Subnet уже существует: $subnetName ($($subnet.id))"
    }

    # Security Group
    $sgsJson = Invoke-Yc vpc security-group list --folder-id $folderId --format json
    $sgs = $sgsJson | ConvertFrom-Json
    $sg = $sgs | Where-Object { $_.name -eq $sgName } | Select-Object -First 1
    if (-not $sg) {
        Write-Info "Создаю security group '$sgName'..."
        $sgCreateArgs = @(
            "vpc", "security-group", "create",
            "--name", $sgName,
            "--description", "MSP Cloud web and mail",
            "--network-id", $net.id,
            "--folder-id", $folderId,
            "--rule", "direction=ingress,port=22,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=SSH",
            "--rule", "direction=ingress,port=80,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=HTTP",
            "--rule", "direction=ingress,port=443,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=HTTPS",
            "--rule", "direction=ingress,port=443,protocol=udp,v4-cidrs=[0.0.0.0/0],description=AmneziaWG-VPN",
            "--rule", "direction=ingress,port=465,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=SMTPS",
            "--rule", "direction=ingress,port=587,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=SMTP-STARTTLS",
            "--rule", "direction=ingress,port=143,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=IMAP",
            "--rule", "direction=ingress,port=993,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=IMAPS",
            "--rule", "direction=ingress,port=4190,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=ManageSieve",
            "--rule", "direction=egress,from-port=0,to-port=65535,protocol=any,v4-cidrs=[0.0.0.0/0],description=All-outbound",
            "--format", "json"
        )
        & yc $sgCreateArgs 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { Write-Fail "Не удалось создать security group"; exit 1 }
        $sgJson = Invoke-Yc vpc security-group get --name $sgName --folder-id $folderId --format json
        $sg = $sgJson | ConvertFrom-Json
        Write-Ok "Security group создана: $sgName ($($sg.id))"
    } else {
        Write-Ok "Security group уже существует: $sgName ($($sg.id))"
    }

    # ═══════════════════════════════════════════════════════════════════
    # Стадия 4: Создание ВМ
    # ═══════════════════════════════════════════════════════════════════
    Write-Stage 4 8 "Создание ВМ ($VmName)"

    if ($Recreate) {
        Write-Warn "Recreate=true → удаляю старую ВМ и весь каталог (ресурсы будут пересозданы)"
        # Удаляем всё: проще удалить каталог и создать заново
        Invoke-Yc resource-manager folder delete --id $folderId --force | Out-Null
        Write-Info "Каталог $folderName удалён. Создаём новый..."
        # Создаём новый каталог с тем же именем (или новым)
        Invoke-Yc resource-manager folder create --name $folderName --cloud-id $cloudId | Out-Null
        $folderJson = Invoke-Yc resource-manager folder get --name $folderName --cloud-id $cloudId --format json
        $folder = $folderJson | ConvertFrom-Json
        $folderId = $folder.id
        Invoke-Yc config set folder-id $folderId | Out-Null
        # Повторяем создание сети и т.д. (можно рекурсивно вызвать скрипт заново, но проще продолжить с новым folderId)
        # Для простоты: выходим с сообщением, чтобы пользователь запустил скрипт ещё раз (без -Recreate)
        Write-Warn "Каталог пересоздан. Пожалуйста, запустите скрипт ещё раз без параметра -Recreate"
        exit 0
    }

    $vmsJson = Invoke-Yc compute instance list --folder-id $folderId --format json
    $vms = $vmsJson | ConvertFrom-Json
    $existingVm = $vms | Where-Object { $_.name -eq $VmName } | Select-Object -First 1

    if ($existingVm) {
        Write-Ok "ВМ уже существует: $VmName ($($existingVm.id))"
        $vmId = $existingVm.id
    } else {
        Write-Info "Подготовка cloud-init..."
        $cloudInitPath = Join-Path $DeployDir "cloud-init.yaml"
        $cloudInitContent = Get-Content -Path $cloudInitPath -Raw
        $cloudInitContent = $cloudInitContent.Replace("__SSH_PUBKEY__", $sshPubKey)
        $cloudInitTemp = Join-Path $env:TEMP "msp-cloud-init.yaml"
        [System.IO.File]::WriteAllText($cloudInitTemp, $cloudInitContent, [System.Text.UTF8Encoding]::new($false))

        Write-Info "Создаю ВМ (1-2 минуты)..."
        $platformId = "standard-v3"
        $coreFraction = if ($Preemptible) { "50" } else { "100" }

        $ubuntuImage = Invoke-Yc compute image get-latest-from-family ubuntu-2204-lts --folder-id standard-images --format json
        $ubuntuImageInfo = $ubuntuImage | ConvertFrom-Json
        $ubuntuImageId = $ubuntuImageInfo.id
        Write-Info "Ubuntu image: $ubuntuImageId"

        $createArgs = @(
            "compute", "instance", "create",
            "--name", $VmName,
            "--zone", $Zone,
            "--folder-id", $folderId,
            "--platform-id", $platformId,
            "--cores", $VmCores,
            "--core-fraction", $coreFraction,
            "--memory", "${VmMemoryGb}GB",
            "--create-boot-disk", "image-id=${ubuntuImageId},size=${VmDiskGb}GB,type=network-ssd",
            "--network-interface", "subnet-name=$subnetName,nat-ip-version=ipv4,security-group-ids=$($sg.id)",
            "--metadata-from-file", "user-data=$cloudInitTemp"
        )
        if ($Preemptible) { $createArgs += "--preemptible" }
        $createArgs += "--format"
        $createArgs += "json"

        $createOutput = & yc $createArgs 2>&1 | Where-Object { $_ -notmatch '^\.\.\.\d+s' -and $_ -notmatch 'done \(' }
        $ycret = $LASTEXITCODE
        if ($ycret -ne 0 -and ($createOutput -match 'ERROR' -or $createOutput -match 'error')) {
            Write-Fail "Не удалось создать ВМ: $createOutput"
            exit 1
        }
        $vmInfo = $createOutput | ConvertFrom-Json
        $vmId = $vmInfo.id
        Write-Ok "ВМ создана: $VmName ($vmId)"
    }

    # ═══════════════════════════════════════════════════════════════════
    # Стадия 5: Ожидание public IP + Static IP + SSH
    # ═══════════════════════════════════════════════════════════════════
    Write-Stage 5 8 "Ожидание готовности ВМ (RUNNING + Static IP + SSH)"

    $publicIp = $null
    for ($i = 1; $i -le 30; $i++) {
        $vmJson = Invoke-Yc compute instance get --id $vmId --format json
        $vm = $vmJson | ConvertFrom-Json
        $publicIp = $vm.network_interfaces[0].primary_v4_address.one_to_one_nat.address
        if ($vm.status -eq "RUNNING" -and $publicIp) {
            Write-Ok "ВМ RUNNING, ephemeral IP: $publicIp"
            break
        }
        Write-Info "Попытка $i/30 · status=$($vm.status)"
        Start-Sleep -Seconds 10
    }
    if (-not $publicIp) { Write-Fail "ВМ не стала RUNNING за 5 минут"; exit 1 }

    # ── Static IP: привязываем к ВМ ──────────────────────────────────
    # Preemptible ВМ получает НОВЫЙ IP при каждом рестарте.
    # Static IP (reserved=true) сохраняется → DNS не устаревает.
    # Стоимость: 189.73₽/мес (≈1.3₽/час). Без него DNS A-запись
    # будет указывать на старый IP после каждого рестарта ВМ.
    $staticIpId = $null
    if ($UseStaticIp) {
        Write-Info "Резервирую static IP в зоне $Zone..."
        $reservedIpsJson = Invoke-Yc vpc address list --folder-id $folderId --format json
        $reservedIps = $reservedIpsJson | ConvertFrom-Json
        $existingReserved = $reservedIps | Where-Object { $_.reserved -eq $true -and $_.type -eq "EXTERNAL" } | Select-Object -First 1

        if ($existingReserved) {
            $publicIp = $existingReserved.address
            $staticIpId = $existingReserved.id
            Write-Ok "Найден зарезервированный static IP: $publicIp ($staticIpId)"
        } else {
            $ipName = "msp-static-ip-${folderName}"
            $createIpOutput = Invoke-Yc vpc address create --name $ipName --folder-id $folderId --zone $Zone --format json
            $newIp = $createIpOutput | ConvertFrom-Json
            $publicIp = $newIp.address
            $staticIpId = $newIp.id
            Write-Ok "Static IP создан: $publicIp ($staticIpId)"
        }

        # Привязываем static IP к ВМ через one-to-one-nat
        # ВАЖНО: yc compute instance add-one-to-one-nat — асинхронная операция.
        # PowerShell 5.1 не может корректно обработать stderr от yc,
        # поэтому используем cmd /c (как и для всех yc-команд).
        Write-Info "Привязываю static IP $publicIp к ВМ $VmName..."
        $natCmd = "yc compute instance add-one-to-one-nat $VmName --nat-address $publicIp --network-interface-index 0 --folder-id $folderId --format json 2>&1"
        $natOutput = cmd /c $natCmd
        if ($LASTEXITCODE -ne 0) {
            Write-Warn "add-one-to-one-nat вернул ошибку (возможно IP уже привязан): $natOutput"
        } else {
            Write-Ok "Static IP $publicIp привязан к ВМ"
        }
    }

    Write-Info "Ждём готовности sshd..."
    $sshReady = $false
    for ($i = 1; $i -le 30; $i++) {
        $sshTest = cmd /c "$SshExe $SshOpts -o ConnectTimeout=5 -i `"$SshKeyPath`" ubuntu@$publicIp echo READY 2>nul"
        if ($sshTest -match "READY") { $sshReady = $true; Write-Ok "SSH готов"; break }
        Write-Info "Попытка $i/30 · sshd ещё не отвечает"
        Start-Sleep -Seconds 10
    }
    if (-not $sshReady) { Write-Fail "SSH не отвечает за 5 минут"; exit 1 }

    # Ждём cloud-init
    Write-Info "Ждём окончания cloud-init..."
    for ($i = 1; $i -le 60; $i++) {
        $baseReady = cmd /c "$SshExe $SshOpts -i `"$SshKeyPath`" ubuntu@$publicIp `"test -f /var/log/msp-deploy.base-ready && echo READY`" 2>nul"
        if ($baseReady -match "READY") { Write-Ok "cloud-init завершён ($i*10s)"; break }
        if ($i -eq 60) { Write-Warn "cloud-init не завершился за 10 минут, продолжаю..." }
        Start-Sleep -Seconds 10
    }

    # Сохраняем state (включая имена уникальных ресурсов и static IP)
    Save-State -State @{
        domain      = $Domain
        folderId    = $folderId
        folderName  = $folderName
        netName     = $netName
        subnetName  = $subnetName
        sgName      = $sgName
        vmId        = $vmId
        vmName      = $VmName
        publicIp    = $publicIp
        staticIpId  = $staticIpId
        useStaticIp = $UseStaticIp
        zone        = $Zone
        created     = (Get-Date -Format "o")
    }

    # ═══════════════════════════════════════════════════════════════════
    # Стадия 6: Загрузка кода через SCP
    # ═══════════════════════════════════════════════════════════════════
    Write-Stage 6 8 "Загрузка кода через SCP"

    $archive = Join-Path $env:TEMP "msp-repo.zip"
    if (Test-Path $archive) { Remove-Item $archive -Force }
    $sevenZip = $null
    if (Test-Path "C:\Program Files\7-Zip\7z.exe") { $sevenZip = "C:\Program Files\7-Zip\7z.exe" }
    elseif (Get-Command 7z -ErrorAction SilentlyContinue) { $sevenZip = "7z" }
    if (-not $sevenZip) { Write-Fail "7-Zip не найден. Установите 7-Zip или добавьте в PATH."; exit 1 }
    Push-Location $RepoRoot
    & $sevenZip a -tzip -mx5 $archive . "-x!.git" "-x!node_modules" "-x!frontend\build" "-x!__pycache__" "-x!.pytest_cache" "-x!*.pyc" "-x!.deploy-state.json" 2>&1 | Out-Null
    Pop-Location
    if (-not (Test-Path $archive)) { Write-Fail "Архив не создан"; exit 1 }
    $archiveSize = (Get-Item $archive).Length / 1MB
    Write-Ok "Архив создан: $([math]::Round($archiveSize,1)) MB"

    Write-Info "Загружаю на ВМ (scp)..."
    # ВАЖНО: SCP через VPN (AmneziaWG) может таймаутиться. Если не работает —
    # используйте base64+SSH для маленьких файлов: echo BASE64 | ssh ... "base64 -d > file"
    cmd /c "scp $SshOpts -i `"$SshKeyPath`" `"$archive`" ubuntu@${publicIp}:/tmp/msp-repo.zip 2>nul"
    if ($LASTEXITCODE -ne 0) { Write-Fail "SCP не сработал"; exit 1 }

    Write-Info "Распаковка на ВМ..."
    cmd /c "$SshExe $SshOpts -i `"$SshKeyPath`" ubuntu@${publicIp} `"sudo apt-get install -y unzip 2>/dev/null && mkdir -p /opt/msp/Newbie && cd /opt/msp/Newbie && unzip -o /tmp/msp-repo.zip && sudo chmod +x /opt/msp/Newbie/deploy/yandex/setup-on-vm.sh`" 2>nul"
    if ($LASTEXITCODE -ne 0) { Write-Fail "Распаковка не удалась"; exit 1 }
    Write-Ok "Код загружен в /opt/msp/Newbie"

    # ═══════════════════════════════════════════════════════════════════
    # Стадия 7: Запуск setup-on-vm.sh
    # ═══════════════════════════════════════════════════════════════════
    Write-Stage 7 8 "Установка приложения на ВМ (build + docker compose up)"

    Write-Info "Запускаю setup-on-vm.sh (3-5 минут)..."
    $setupCmd = "export MSP_DOMAIN=$Domain && bash /opt/msp/Newbie/deploy/yandex/setup-on-vm.sh 2>&1"
    cmd /c "$SshExe $SshOpts -i `"$SshKeyPath`" ubuntu@$publicIp `"$setupCmd`" 2>nul" | Tee-Object -FilePath $LogFile -Append
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "setup-on-vm.sh завершился с ошибкой. Смотри $LogFile"
        exit 1
    }
    Write-Ok "Приложение установлено и запущено"

    # ═══════════════════════════════════════════════════════════════════
    # Стадия 8: Финальный healthcheck + вывод инструкций
    # ═══════════════════════════════════════════════════════════════════
    Write-Stage 8 8 "Финальная проверка + DNS инструкции"

    $healthOutput = cmd /c "$SshExe $SshOpts -i `"$SshKeyPath`" ubuntu@$publicIp `"curl -sS http://127.0.0.1:8001/api/health`" 2>nul"
    Write-Info "  /api/health → $healthOutput"
    if (-not $SkipMail) {
        $stalwartCheck = cmd /c "$SshExe $SshOpts -i `"$SshKeyPath`" ubuntu@$publicIp `"curl -fsS -o /dev/null -w '%%{http_code}' http://127.0.0.1:8080/`" 2>nul"
        Write-Info "  Stalwart admin :8080 → HTTP $stalwartCheck"
    }

    # Вывод финальной информации
    Write-Host ""
    Write-Host "  +--------------------------------------------------------------+" -ForegroundColor Green
    Write-Host "  |                  DEPLOY COMPLETE                              |" -ForegroundColor Green
    Write-Host "  +--------------------------------------------------------------+" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Public IP:  $publicIp $(if($UseStaticIp){"(static, ID: $staticIpId)"}else{"(ephemeral)"})" -ForegroundColor Yellow
    Write-Host "  Folder:     $folderName" -ForegroundColor Cyan
    Write-Host "  Network:    $netName" -ForegroundColor DarkGray
    if ($UseStaticIp) {
        Write-Host ""
        Write-Host "  DNS A records (Namecheap):" -ForegroundColor Yellow
        Write-Host "    @   -> $publicIp" -ForegroundColor White
        Write-Host "    www -> $publicIp" -ForegroundColor White
        Write-Host "    mail -> $publicIp" -ForegroundColor White
        Write-Host "    vault -> $publicIp" -ForegroundColor White
        Write-Host "    bastion -> $publicIp" -ForegroundColor White
    }
    Write-Host ""
    Write-Host "  Deploy log: $LogFile" -ForegroundColor DarkGray
    Write-Host "  State file: $StateFile" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "PUBLIC_IP=$publicIp" -ForegroundColor White

} finally {
    # Восстановление кодировки
    try { if ($null -ne $script:__PrevConsoleOutputEncoding) { [Console]::OutputEncoding = $script:__PrevConsoleOutputEncoding } } catch { }
    try { $OutputEncoding = $script:__PrevOutputEncoding } catch { }
}