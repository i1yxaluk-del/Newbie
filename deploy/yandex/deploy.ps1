<#
.SYNOPSIS
    Автоматическое развёртывание МСП Облако в Yandex Cloud.

.DESCRIPTION
    Создаёт ВМ в Yandex Cloud, ставит на неё Docker + Caddy + Stalwart Mail
    + бэкенд (FastAPI + MongoDB) + фронт (React static), и выводит IP-адрес
    для установки в DNS.

    Скрипт идемпотентный: повторный запуск пересоздаёт только те ресурсы,
    которых не существует. Для полного пересоздания см. -Recreate.

.PARAMETER Domain
    Домен сайта. Default: mcp-claude.online.

.PARAMETER Zone
    Yandex Cloud зона. Default: ru-central1-a.

.PARAMETER VmName
    Имя ВМ. Default: msp-cloud-vm.

.PARAMETER VmCores
    Количество vCPU. Default: 2.

.PARAMETER VmMemoryGb
    Память в GB. Default: 4.

.PARAMETER VmDiskGb
    Размер boot-диска в GB. Default: 50 (хватит на фронт + бэк + Stalwart mail).

.PARAMETER Preemptible
    Прерываемая ВМ (cheaper, может рестартовать раз в сутки). Default: $true.

.PARAMETER Recreate
    Удалить старую ВМ и создать с нуля. ВНИМАНИЕ: потеряет данные MongoDB!

.PARAMETER SkipMail
    Не настраивать Stalwart почту. Только лендинг + бэк.

.EXAMPLE
    PS C:\msp\Newbie> .\deploy\yandex\deploy.ps1
    Развернуть с дефолтами (mcp-claude.online, ru-central1-a).

.EXAMPLE
    PS C:\msp\Newbie> .\deploy\yandex\deploy.ps1 -Recreate
    Удалить старую ВМ и создать с нуля.

.NOTES
    Требует:
      - Windows 10 build 1803+ (OpenSSH client встроен)
      - PowerShell 5.1+ (что есть в Win10 по умолчанию)
      - Интернет
      - Yandex Cloud аккаунт с привязанной картой

    OAuth токен Yandex Cloud получается автоматически: скрипт открывает
    браузер на странице авторизации, пользователь даёт согласие, копирует
    токен в окно скрипта. Токен сохраняется в %USERPROFILE%\.yc-config\
    через yc CLI, в файлы скрипта НЕ записывается.

    Логи деплоя: %TEMP%\msp-deploy-*.log
#>

[CmdletBinding()]
param(
    [string]$Domain = "mcp-claude.online",
    [string]$Zone = "ru-central1-a",
    [string]$VmName = "msp-cloud-vm",
    [int]$VmCores = 2,
    [int]$VmMemoryGb = 4,
    [int]$VmDiskGb = 50,
    [bool]$Preemptible = $true,
    [switch]$Recreate,
    [switch]$SkipMail
)

# ═══════════════════════════════════════════════════════════════════
# Глобальные настройки
# ═══════════════════════════════════════════════════════════════════
$ErrorActionPreference = "Stop"

# Принудительно ставим UTF-8 для консоли — иначе на русской Windows 10 PowerShell 5.1
# покажет крокозябры вместо кириллицы и Unicode box-drawing.
try {
    $OutputEncoding = New-Object System.Text.UTF8Encoding $false
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    [Console]::InputEncoding  = [System.Text.Encoding]::UTF8
    if (Get-Command chcp -ErrorAction SilentlyContinue) { chcp 65001 > $null }
} catch { }
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$DeployDir = $PSScriptRoot
$StateFile = Join-Path $DeployDir ".deploy-state.json"
$LogFile = Join-Path $env:TEMP ("msp-deploy-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
$SshKeyPath = Join-Path $env:USERPROFILE ".ssh\id_ed25519_yc"
$SshKeyPubPath = "$SshKeyPath.pub"

# Цветной вывод стадий
function Write-Stage {
    param([int]$Num, [int]$Total, [string]$Text)
    Write-Host ""
    Write-Host ("═══ [{0}/{1}] {2} ═══" -f $Num, $Total, $Text) -ForegroundColor Cyan
    Add-Content -Path $LogFile -Value ("[{0}] STAGE {1}/{2}: {3}" -f (Get-Date -Format "HH:mm:ss"), $Num, $Total, $Text)
}

function Write-Info { param([string]$Text) Write-Host "  $Text" -ForegroundColor Gray; Add-Content -Path $LogFile -Value "  $Text" }
function Write-Ok   { param([string]$Text) Write-Host "  ✓ $Text" -ForegroundColor Green; Add-Content -Path $LogFile -Value "  OK: $Text" }
function Write-Warn { param([string]$Text) Write-Host "  ! $Text" -ForegroundColor Yellow; Add-Content -Path $LogFile -Value "  WARN: $Text" }
function Write-Fail { param([string]$Text) Write-Host "  ✗ $Text" -ForegroundColor Red; Add-Content -Path $LogFile -Value "  FAIL: $Text" }

function Save-State {
    param([hashtable]$State)
    $State | ConvertTo-Json -Depth 5 | Out-File -FilePath $StateFile -Encoding utf8
}

function Load-State {
    if (Test-Path $StateFile) {
        return Get-Content -Path $StateFile -Raw | ConvertFrom-Json
    }
    return $null
}

# ═══════════════════════════════════════════════════════════════════
# Заголовок
# ═══════════════════════════════════════════════════════════════════
Clear-Host
Write-Host @"

  ╔════════════════════════════════════════════════════════════════╗
  ║   МСП Облако · автоматический деплой в Yandex Cloud           ║
  ╠════════════════════════════════════════════════════════════════╣
  ║                                                                ║
  ║   Домен:    $($Domain.PadRight(52))║
  ║   Зона:     $($Zone.PadRight(52))║
  ║   ВМ:       $($VmName) ($VmCores vCPU / $VmMemoryGb GB / $VmDiskGb GB SSD)$((" " * (52 - "$VmName ($VmCores vCPU / $VmMemoryGb GB / $VmDiskGb GB SSD)".Length)))║
  ║   Тип:      $(if($Preemptible){"прерываемая (дешевле)"}else{"гарантированная"})$((" " * (52 - $(if($Preemptible){"прерываемая (дешевле)".Length}else{"гарантированная".Length}))))║
  ║   Почта:    $(if($SkipMail){"пропущено"}else{"Stalwart (admin@/sales@/alert@)"})$((" " * (52 - $(if($SkipMail){"пропущено".Length}else{"Stalwart (admin@/sales@/alert@)".Length}))))║
  ║                                                                ║
  ║   Логи:     $($LogFile)$((" " * (52 - $LogFile.Length)))║
  ║                                                                ║
  ╚════════════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

# ═══════════════════════════════════════════════════════════════════
# Стадия 1: yc CLI + SSH client
# ═══════════════════════════════════════════════════════════════════
Write-Stage 1 8 "Проверка yc CLI и SSH"

# yc CLI
$ycCmd = Get-Command yc -ErrorAction SilentlyContinue
if (-not $ycCmd) {
    Write-Info "yc CLI не найден, устанавливаю..."
    $ycInstaller = Join-Path $env:TEMP "yc-install.ps1"
    try {
        Invoke-WebRequest -Uri "https://storage.yandexcloud.net/yandexcloud-yc/install.ps1" -OutFile $ycInstaller -UseBasicParsing
        & powershell -ExecutionPolicy Bypass -File $ycInstaller -n
        # Добавляем в PATH текущей сессии
        $env:Path += ";$env:USERPROFILE\yandex-cloud\bin"
        $ycCmd = Get-Command yc -ErrorAction SilentlyContinue
        if (-not $ycCmd) {
            Write-Fail "yc CLI не установился. Скачайте вручную: https://yandex.cloud/ru/docs/cli/quickstart"
            exit 1
        }
        Write-Ok "yc CLI установлен"
    } catch {
        Write-Fail "Не удалось скачать yc-installer: $_"
        Write-Info "Скачайте вручную: https://yandex.cloud/ru/docs/cli/quickstart"
        exit 1
    }
} else {
    Write-Ok "yc CLI: $(yc version 2>&1 | Select-Object -First 1)"
}

# SSH client (Windows 10 1803+ built-in)
$sshCmd = Get-Command ssh -ErrorAction SilentlyContinue
if (-not $sshCmd) {
    Write-Fail "SSH client не найден. Windows 10 build 1803+ требуется."
    Write-Info "Включите: Settings → Apps → Optional features → OpenSSH Client"
    exit 1
}
Write-Ok "SSH client: $(ssh -V 2>&1)"

# SCP client
$scpCmd = Get-Command scp -ErrorAction SilentlyContinue
if (-not $scpCmd) {
    Write-Fail "SCP client не найден (входит в OpenSSH Client)."
    exit 1
}
Write-Ok "SCP client доступен"

# ═══════════════════════════════════════════════════════════════════
# Стадия 2: OAuth + профиль yc
# ═══════════════════════════════════════════════════════════════════
Write-Stage 2 8 "Авторизация в Yandex Cloud"

# Проверяем существует ли активный профиль
$ycProfile = & yc config list 2>&1 | Out-String
if ($LASTEXITCODE -ne 0 -or $ycProfile -notmatch "token:") {
    Write-Info "Нет активного yc-профиля. Открываю браузер для OAuth..."

    $oauthUrl = "https://oauth.yandex.com/authorize?response_type=token&client_id=1a6990aa636648e9b2ef855fa7bec2fb"
    Start-Process $oauthUrl

    Write-Host ""
    Write-Host "  В браузере:" -ForegroundColor Yellow
    Write-Host "    1. Нажмите 'Разрешить'" -ForegroundColor Yellow
    Write-Host "    2. Скопируйте OAuth-токен из адресной строки или со страницы" -ForegroundColor Yellow
    Write-Host ""
    $token = Read-Host -Prompt "  Вставьте OAuth-токен"

    if ([string]::IsNullOrWhiteSpace($token)) {
        Write-Fail "Пустой токен. Прерываю."
        exit 1
    }

    # Создаём профиль 'msp-cloud'
    & yc config profile create msp-cloud 2>&1 | Out-Null
    & yc config profile activate msp-cloud 2>&1 | Out-Null
    & yc config set token $token 2>&1 | Out-Null

    Write-Ok "Профиль 'msp-cloud' создан, токен сохранён в %USERPROFILE%\.yc-config\"
} else {
    Write-Ok "yc-профиль активен"
}

# Создаём облако и каталог если их нет (для совсем новых аккаунтов yc cloud create требуется)
$clouds = & yc resource-manager cloud list --format json 2>$null | ConvertFrom-Json
if (-not $clouds -or $clouds.Count -eq 0) {
    Write-Fail "У вас нет облака в Yandex Cloud. Зайдите в https://console.cloud.yandex.ru/ и создайте облако вручную (привязка карты)."
    exit 1
}

$cloudId = $clouds[0].id
& yc config set cloud-id $cloudId 2>&1 | Out-Null
Write-Info "Cloud: $($clouds[0].name) ($cloudId)"

# Каталог (folder)
$folders = & yc resource-manager folder list --cloud-id $cloudId --format json 2>$null | ConvertFrom-Json
$folder = $folders | Where-Object { $_.name -eq "msp-cloud" } | Select-Object -First 1
if (-not $folder) {
    Write-Info "Создаю каталог 'msp-cloud'..."
    & yc resource-manager folder create --name msp-cloud --cloud-id $cloudId 2>&1 | Out-Null
    $folder = & yc resource-manager folder get --name msp-cloud --cloud-id $cloudId --format json | ConvertFrom-Json
}
$folderId = $folder.id
& yc config set folder-id $folderId 2>&1 | Out-Null
& yc config set compute-default-zone $Zone 2>&1 | Out-Null
Write-Ok "Folder: msp-cloud ($folderId)"

# ═══════════════════════════════════════════════════════════════════
# Стадия 3: SSH key + VPC + Subnet + Security Group
# ═══════════════════════════════════════════════════════════════════
Write-Stage 3 8 "SSH ключ + сеть"

# SSH ключ (ed25519, без пароля)
if (-not (Test-Path $SshKeyPath)) {
    Write-Info "Генерирую SSH-ключ ed25519 в $SshKeyPath..."
    $sshDir = Split-Path $SshKeyPath -Parent
    if (-not (Test-Path $sshDir)) { New-Item -ItemType Directory -Path $sshDir | Out-Null }
    & ssh-keygen -t ed25519 -f $SshKeyPath -N '""' -C "msp-yc-deploy" 2>&1 | Out-Null
    Write-Ok "SSH ключ создан"
} else {
    Write-Ok "SSH ключ существует: $SshKeyPath"
}
$sshPubKey = (Get-Content -Path $SshKeyPubPath -Raw).Trim()

# VPC
$networks = & yc vpc network list --folder-id $folderId --format json | ConvertFrom-Json
$net = $networks | Where-Object { $_.name -eq "msp-net" } | Select-Object -First 1
if (-not $net) {
    Write-Info "Создаю VPC 'msp-net'..."
    & yc vpc network create --name msp-net --folder-id $folderId 2>&1 | Out-Null
    $net = & yc vpc network get --name msp-net --folder-id $folderId --format json | ConvertFrom-Json
}
Write-Ok "VPC: msp-net ($($net.id))"

# Subnet
$subnets = & yc vpc subnet list --folder-id $folderId --format json | ConvertFrom-Json
$subnet = $subnets | Where-Object { $_.name -eq "msp-subnet" -and $_.zone_id -eq $Zone } | Select-Object -First 1
if (-not $subnet) {
    Write-Info "Создаю subnet 'msp-subnet' в $Zone..."
    & yc vpc subnet create `
        --name msp-subnet `
        --network-id $net.id `
        --zone $Zone `
        --range 10.10.0.0/24 `
        --folder-id $folderId 2>&1 | Out-Null
    $subnet = & yc vpc subnet get --name msp-subnet --folder-id $folderId --format json | ConvertFrom-Json
}
Write-Ok "Subnet: msp-subnet ($($subnet.id), 10.10.0.0/24)"

# Security Group: SSH + HTTP/S + Mail
$sgs = & yc vpc security-group list --folder-id $folderId --format json 2>$null | ConvertFrom-Json
$sg = $sgs | Where-Object { $_.name -eq "msp-sg" } | Select-Object -First 1
if (-not $sg) {
    Write-Info "Создаю security group 'msp-sg' (SSH/HTTP/HTTPS/SMTP/IMAP)..."

    # Создаём с inline-правилами в одном вызове
    & yc vpc security-group create `
        --name msp-sg `
        --description "MSP Cloud: web + mail ports" `
        --network-id $net.id `
        --folder-id $folderId `
        --rule "direction=ingress,port=22,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=SSH" `
        --rule "direction=ingress,port=80,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=HTTP/ACME" `
        --rule "direction=ingress,port=443,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=HTTPS" `
        --rule "direction=ingress,port=25,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=SMTP-MX" `
        --rule "direction=ingress,port=465,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=SMTPS" `
        --rule "direction=ingress,port=587,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=SMTP-Submission" `
        --rule "direction=ingress,port=143,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=IMAP" `
        --rule "direction=ingress,port=993,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=IMAPS" `
        --rule "direction=ingress,port=4190,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=ManageSieve" `
        --rule "direction=egress,from-port=0,to-port=65535,protocol=any,v4-cidrs=[0.0.0.0/0],description=All-outbound" `
        2>&1 | Out-Null

    $sg = & yc vpc security-group get --name msp-sg --folder-id $folderId --format json | ConvertFrom-Json
}
Write-Ok "Security group: msp-sg ($($sg.id))"

# ═══════════════════════════════════════════════════════════════════
# Стадия 4: Создание ВМ
# ═══════════════════════════════════════════════════════════════════
Write-Stage 4 8 "Создание ВМ ($VmName)"

if ($Recreate) {
    Write-Warn "Recreate=true → удаляю старую ВМ если есть"
    & yc compute instance delete --name $VmName --folder-id $folderId 2>&1 | Out-Null
}

$existingVm = & yc compute instance list --folder-id $folderId --format json 2>$null | ConvertFrom-Json | Where-Object { $_.name -eq $VmName } | Select-Object -First 1

if ($existingVm) {
    Write-Ok "ВМ уже существует: $VmName ($($existingVm.id))"
    $vmId = $existingVm.id
} else {
    Write-Info "Подготовка cloud-init..."

    # Подставляем SSH pubkey в cloud-init.yaml
    $cloudInitPath = Join-Path $DeployDir "cloud-init.yaml"
    $cloudInitContent = Get-Content -Path $cloudInitPath -Raw
    $cloudInitContent = $cloudInitContent.Replace("__SSH_PUBKEY__", $sshPubKey)

    $cloudInitTemp = Join-Path $env:TEMP "msp-cloud-init.yaml"
    [System.IO.File]::WriteAllText($cloudInitTemp, $cloudInitContent, [System.Text.UTF8Encoding]::new($false))

    Write-Info "Создаю ВМ (это займёт 1-2 минуты)..."

    # Ubuntu 22.04 LTS standard image
    $platformId = "standard-v3"
    $coreFraction = if ($Preemptible) { "50" } else { "100" }

    $createCmd = @(
        "compute", "instance", "create",
        "--name", $VmName,
        "--zone", $Zone,
        "--folder-id", $folderId,
        "--platform-id", $platformId,
        "--cores", $VmCores,
        "--core-fraction", $coreFraction,
        "--memory", "${VmMemoryGb}GB",
        "--create-boot-disk", "image-family=ubuntu-2204-lts,size=${VmDiskGb}GB,type=network-ssd",
        "--network-interface", "subnet-name=msp-subnet,nat-ip-version=ipv4,security-group-ids=$($sg.id)",
        "--ssh-key", $SshKeyPubPath,
        "--metadata-from-file", "user-data=$cloudInitTemp"
    )
    if ($Preemptible) { $createCmd += "--preemptible" }

    $createOutput = & yc @createCmd --format json 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Не удалось создать ВМ:"
        Write-Host $createOutput
        exit 1
    }

    $vmInfo = $createOutput | ConvertFrom-Json
    $vmId = $vmInfo.id
    Write-Ok "ВМ создана: $VmName ($vmId)"
}

# ═══════════════════════════════════════════════════════════════════
# Стадия 5: Ждём public IP + SSH
# ═══════════════════════════════════════════════════════════════════
Write-Stage 5 8 "Ожидание готовности ВМ (RUNNING + SSH)"

$publicIp = $null
for ($i = 1; $i -le 30; $i++) {
    $vm = & yc compute instance get --id $vmId --format json | ConvertFrom-Json
    $publicIp = $vm.network_interfaces[0].primary_v4_address.one_to_one_nat.address
    if ($vm.status -eq "RUNNING" -and $publicIp) {
        Write-Ok "ВМ RUNNING, public IP: $publicIp"
        break
    }
    Write-Info "Попытка $i/30 · status=$($vm.status)"
    Start-Sleep -Seconds 10
}

if (-not $publicIp) {
    Write-Fail "ВМ не стала RUNNING за 5 минут"
    exit 1
}

# Ждём SSH
Write-Info "Ждём готовности sshd..."
$sshReady = $false
for ($i = 1; $i -le 30; $i++) {
    $sshTest = & ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -i $SshKeyPath ubuntu@$publicIp "echo READY" 2>$null
    if ($sshTest -eq "READY") {
        Write-Ok "SSH готов"
        $sshReady = $true
        break
    }
    Write-Info "Попытка $i/30 · sshd ещё не отвечает"
    Start-Sleep -Seconds 10
}

if (-not $sshReady) {
    Write-Fail "SSH не отвечает за 5 минут"
    exit 1
}

# Ждём окончания cloud-init (base-ready marker)
Write-Info "Ждём окончания cloud-init (Docker / Caddy / Node устанавливаются)..."
for ($i = 1; $i -le 60; $i++) {
    $baseReady = & ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i $SshKeyPath ubuntu@$publicIp "test -f /var/log/msp-deploy.base-ready && echo READY" 2>$null
    if ($baseReady -eq "READY") {
        Write-Ok "cloud-init завершён ($i*10s)"
        break
    }
    if ($i -eq 60) {
        Write-Warn "cloud-init не завершился за 10 минут, продолжаю — возможно базовая установка ещё идёт"
    }
    Start-Sleep -Seconds 10
}

# Сохраняем state
Save-State -State @{
    domain      = $Domain
    folderId    = $folderId
    vmId        = $vmId
    vmName      = $VmName
    publicIp    = $publicIp
    zone        = $Zone
    created     = (Get-Date -Format "o")
}

# ═══════════════════════════════════════════════════════════════════
# Стадия 6: Загрузка кода
# ═══════════════════════════════════════════════════════════════════
Write-Stage 6 8 "Загрузка кода через SCP"

Write-Info "Создаю tarball без node_modules / .git / build..."
$tarball = Join-Path $env:TEMP "msp-repo.tar.gz"
if (Test-Path $tarball) { Remove-Item $tarball -Force }

# tar входит в Windows 10 1803+
Push-Location $RepoRoot
& tar `
    --exclude=".git" `
    --exclude="node_modules" `
    --exclude="frontend/build" `
    --exclude="__pycache__" `
    --exclude=".pytest_cache" `
    --exclude="*.pyc" `
    --exclude=".deploy-state.json" `
    -czf $tarball .
Pop-Location

if (-not (Test-Path $tarball)) {
    Write-Fail "tar не создал tarball"
    exit 1
}
$tarSize = (Get-Item $tarball).Length / 1MB
Write-Ok ("Tarball создан: {0:N1} MB" -f $tarSize)

Write-Info "Загружаю на ВМ (scp)..."
& scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i $SshKeyPath $tarball ubuntu@${publicIp}:/tmp/msp-repo.tar.gz 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Fail "SCP не сработал"
    exit 1
}

Write-Info "Распаковка на ВМ..."
$unpackCmd = "mkdir -p /opt/msp/Newbie && tar xzf /tmp/msp-repo.tar.gz -C /opt/msp/Newbie && chmod +x /opt/msp/Newbie/deploy/yandex/setup-on-vm.sh"
& ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i $SshKeyPath ubuntu@$publicIp $unpackCmd
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Распаковка не удалась"
    exit 1
}
Write-Ok "Код загружен в /opt/msp/Newbie"

# ═══════════════════════════════════════════════════════════════════
# Стадия 7: Запуск setup-on-vm.sh
# ═══════════════════════════════════════════════════════════════════
Write-Stage 7 8 "Установка приложения на ВМ (build + docker compose up)"

Write-Info "Запускаю setup-on-vm.sh (yarn build, .env, docker compose)... это 3-5 минут"

$setupCmd = "export MSP_DOMAIN=$Domain && bash /opt/msp/Newbie/deploy/yandex/setup-on-vm.sh 2>&1"
& ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i $SshKeyPath ubuntu@$publicIp $setupCmd 2>&1 | Tee-Object -FilePath $LogFile -Append

if ($LASTEXITCODE -ne 0) {
    Write-Fail "setup-on-vm.sh завершился с ошибкой. Смотри $LogFile"
    Write-Info "Для отладки: ssh -i `"$SshKeyPath`" ubuntu@$publicIp"
    Write-Info "Логи на ВМ: tail -100 /var/log/msp-deploy.log"
    exit 1
}

Write-Ok "Приложение установлено и запущено"

# ═══════════════════════════════════════════════════════════════════
# Стадия 8: Финальный healthcheck + вывод инструкций
# ═══════════════════════════════════════════════════════════════════
Write-Stage 8 8 "Финальная проверка + DNS инструкции"

# Локальный (по IP) /api/health — проверка что бэк жив
Write-Info "Локальный healthcheck (по IP, без HTTPS)..."
$healthCmd = "curl -sS http://127.0.0.1:8001/api/health"
$healthOutput = & ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i $SshKeyPath ubuntu@$publicIp $healthCmd 2>&1
Write-Info "  /api/health → $healthOutput"

# Stalwart admin доступен?
if (-not $SkipMail) {
    $stalwartCheck = & ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i $SshKeyPath ubuntu@$publicIp "curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/ 2>&1" 2>&1
    Write-Info "  Stalwart admin :8080 → HTTP $stalwartCheck"
}

# Финальный вывод
Write-Host ""
Write-Host @"

  ╔════════════════════════════════════════════════════════════════╗
  ║                  ✓ ДЕПЛОЙ ЗАВЕРШЁН                            ║
  ╚════════════════════════════════════════════════════════════════╝

"@ -ForegroundColor Green

Write-Host "  Public IP: " -NoNewline -ForegroundColor White
Write-Host $publicIp -ForegroundColor Yellow -BackgroundColor DarkGray
Write-Host ""
Write-Host "  ┌─ DNS-записи: добавьте у регистратора домена $Domain ─────────" -ForegroundColor White
Write-Host ""
Write-Host "  Тип   Имя                              Значение" -ForegroundColor DarkGray
Write-Host "  ───   ──────────────────────────────   ────────────────────────────────" -ForegroundColor DarkGray
Write-Host ("  A     {0,-32}   {1}" -f $Domain, $publicIp) -ForegroundColor White
Write-Host ("  A     www.{0,-28}   {1}" -f $Domain, $publicIp) -ForegroundColor White
if (-not $SkipMail) {
Write-Host ("  A     mail.{0,-27}   {1}" -f $Domain, $publicIp) -ForegroundColor White
Write-Host ("  MX    {0,-32}   10 mail.{1}" -f $Domain, $Domain) -ForegroundColor White
Write-Host ("  TXT   {0,-32}   v=spf1 a mx ip4:{1} -all" -f $Domain, $publicIp) -ForegroundColor White
Write-Host ("  TXT   _dmarc.{0,-26}   v=DMARC1; p=quarantine; rua=mailto:admin@{1}" -f $Domain, $Domain) -ForegroundColor White
Write-Host ""
Write-Host "  Для DKIM:" -ForegroundColor DarkGray
Write-Host "    1. После DNS-propagation войдите в админку Stalwart:" -ForegroundColor DarkGray
Write-Host "         ssh -L 8080:localhost:8080 -i `"$SshKeyPath`" ubuntu@$publicIp" -ForegroundColor Yellow
Write-Host "         → откройте http://localhost:8080/admin" -ForegroundColor DarkGray
Write-Host "    2. Settings → Domains → $Domain → Generate DKIM key" -ForegroundColor DarkGray
Write-Host "    3. Скопируйте TXT-запись и добавьте в DNS" -ForegroundColor DarkGray
}
Write-Host ""
Write-Host "  ┌─ После DNS-propagation (5-30 мин) ──────────────────────────" -ForegroundColor White
Write-Host "    https://$Domain                     · лендинг" -ForegroundColor Cyan
Write-Host "    https://$Domain/admin               · админка лидов" -ForegroundColor Cyan
Write-Host "    https://$Domain/api/health          · health-чек" -ForegroundColor Cyan
if (-not $SkipMail) {
Write-Host "    SMTP submit: $Domain:587 (STARTTLS) · sales@/alert@ креды на ВМ" -ForegroundColor Cyan
Write-Host "    IMAP  read:  $Domain:993 (TLS)      · для Thunderbird/Outlook" -ForegroundColor Cyan
}
Write-Host ""
Write-Host "  ┌─ ВАЖНО ─────────────────────────────────────────────────────" -ForegroundColor Yellow
Write-Host "    Пароли (ADMIN_TOKEN, Stalwart admin, mailbox passwords) на ВМ:" -ForegroundColor Yellow
Write-Host "      ssh -i `"$SshKeyPath`" ubuntu@$publicIp cat msp-deploy-secrets.txt" -ForegroundColor Yellow
Write-Host "    Скопируйте этот файл к себе и удалите его с ВМ:" -ForegroundColor Yellow
Write-Host "      ssh -i `"$SshKeyPath`" ubuntu@$publicIp shred -u msp-deploy-secrets.txt" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Логи деплоя: $LogFile" -ForegroundColor DarkGray
Write-Host "  State:       $StateFile (не коммитить!)" -ForegroundColor DarkGray
Write-Host ""

# В отдельный stdout-блок выводим только IP — для скриптов/CI
[Console]::Out.Flush()
Write-Host "PUBLIC_IP=$publicIp" -ForegroundColor White
