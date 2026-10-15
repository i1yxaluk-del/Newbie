/* Local training UI translation for Wazuh 4.14.5 hard-coded home labels.
 * Exact text replacements only; raw alerts, code and input fields are excluded.
 * No network requests, analytics or third-party translation services.
 */
(() => {
  const translations = new Map(Object.entries({
    "This instance has no agents registered.": "В этом экземпляре пока нет зарегистрированных агентов.",
    "Please deploy agents to begin monitoring your endpoints.": "Установите агенты, чтобы начать мониторинг конечных устройств.",
    "Deploy new agent": "Установить новый агент",
    "Agents summary": "Сводка по агентам",
    "Critical severity": "Критическая важность",
    "High severity": "Высокая важность",
    "Medium severity": "Средняя важность",
    "Low severity": "Низкая важность",
    "Rule level 15 or higher": "Уровень правила 15 и выше",
    "Rule level 12 to 14": "Уровень правила от 12 до 14",
    "Rule level 7 to 11": "Уровень правила от 7 до 11",
    "Rule level 0 to 6": "Уровень правила от 0 до 6",
    "Last 24 hours alerts": "Оповещения за последние 24 часа",
    "Configuration Assessment": "Оценка конфигурации",
    "Scan your assets as part of a configuration assessment audit.": "Проверяйте ресурсы в рамках аудита конфигурации.",
    "Malware Detection": "Обнаружение вредоносного ПО",
    "Check indicators of compromise triggered by malware infections or cyberattacks.": "Проверяйте индикаторы компрометации, связанные с вредоносным ПО или кибератаками.",
    "File Integrity Monitoring": "Контроль целостности файлов",
    "Alerts related to file changes, including permissions, content, ownership, and attributes.": "Оповещения об изменении файлов: прав, содержимого, владельцев и атрибутов.",
    "Endpoint security": "Защита конечных устройств",
    "Threat Hunting": "Поиск угроз",
    "Browse through your security alerts, identifying issues and threats in your environment.": "Исследуйте оповещения безопасности для выявления проблем и угроз в своей среде.",
    "Vulnerability Detection": "Обнаружение уязвимостей",
    "Discover what applications in your environment are affected by well-known vulnerabilities.": "Определяйте приложения в своей среде, затронутые известными уязвимостями.",
    "Explore security alerts mapped to adversary tactics and techniques for better threat understanding.": "Исследуйте оповещения, сопоставленные с тактиками и техниками атакующих, для понимания угроз.",
    "Threat intelligence": "Аналитика угроз",
    "IT Hygiene": "IT-гигиена",
    "Assess system, software, processes, and network layers to detect misconfigurations, unauthorized changes, and anomalies.": "Проверяйте системы, ПО, процессы и сеть для выявления ошибок конфигурации, несанкционированных изменений и аномалий.",
    "Global security standard for entities that process, store, or transmit payment cardholder data.": "Международный стандарт безопасности для организаций, обрабатывающих, хранящих или передающих данные платёжных карт.",
    "General Data Protection Regulation (GDPR) sets guidelines for processing of personal data.": "Общий регламент защиты данных GDPR устанавливает требования к обработке персональных данных.",
    "Health Insurance Portability and Accountability Act of 1996 (HIPAA) provides data privacy and security provisions for safeguarding medical information.": "Закон США HIPAA устанавливает требования к конфиденциальности и безопасности медицинской информации.",
    "National Institute of Standards and Technology Special Publication 800-53 (NIST 800-53) sets guidelines for federal information systems.": "Публикация NIST 800-53 содержит рекомендации по защите федеральных информационных систем США.",
    "Trust Services Criteria for Security, Availability, Processing Integrity, Confidentiality, and Privacy.": "Критерии доверенных услуг: безопасность, доступность, целостность обработки, конфиденциальность и защита персональных данных.",
    "Security operations": "Операции безопасности",
    "Monitor and collect the activity from Docker containers such as creation, running, starting, stopping or pausing events.": "Собирайте события Docker: создание, работа, запуск, остановка и приостановка контейнеров.",
    "Security events related to your Amazon AWS services, collected directly via AWS API.": "События безопасности сервисов Amazon AWS, получаемые через AWS API.",
    "Security events related to your Google Cloud Platform services, collected directly via GCP API.": "События безопасности Google Cloud Platform, получаемые через GCP API.",
    "Monitoring events from audit logs of your GitHub organizations.": "Мониторинг событий журналов аудита организаций GitHub.",
    "Security events related to your Office 365 services.": "События безопасности сервисов Office 365.",
    "Security events related to your Microsoft Graph services, collected directly via Microsoft Graph API.": "События безопасности Microsoft Graph, получаемые через Microsoft Graph API."
  }));
  const excluded = "script,style,code,pre,input,textarea,[contenteditable=true],[data-test-subj*=docViewer],[data-test-subj*=discoverDocTable]";
  function translate(root) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const changes = [];
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (!node.parentElement || node.parentElement.closest(excluded)) continue;
      const text = node.nodeValue.trim();
      if (translations.has(text)) changes.push([node, translations.get(text)]);
    }
    for (const [node, value] of changes) node.nodeValue = value;
  }
  let scheduled = false;
  const observer = new MutationObserver(() => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      observer.disconnect();
      translate(document.body);
      observer.observe(document.body, {childList: true, subtree: true, characterData: true});
      scheduled = false;
    });
  });
  function start() {
    translate(document.body);
    observer.observe(document.body, {childList: true, subtree: true, characterData: true});
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, {once: true});
  else start();
})();
