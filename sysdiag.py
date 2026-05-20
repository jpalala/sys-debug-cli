
#!/usr/bin/env python3

import re
import sys
from dataclasses import dataclass
from typing import list

" Basic - Since Python 3.7, the @dataclass  simplifies class definitions by using type hints to determine fields and then writing the underlying code for you
@dataclass
class Diagnostic:
    key: str
    title: str
    patterns: list[str]
    commands: list[str]
    notes: list[str]


DIAGNOSTICS = [
    Diagnostic(
        key="git_deploy_state",
        title="Inspect git deployment state directly on production",
        patterns=[
            r"\bgit\b",
            r"\bbranch\b",
            r"\bdeployment\b",
            r"\bdeployed\b",
            r"\bproduction\b",
            r"\bcommit\b",
        ],
        commands=[
            "cd /var/www/YOUR_APP",
            "git status",
            "git branch --show-current",
            "git rev-parse HEAD",
            "git log -1 --oneline",
            "git remote -v",
            "git fetch --all --prune",
            "git status -sb",
            "git log --oneline --decorate --graph -10",
        ],
        notes=[
            "Do not run git pull blindly on production.",
            "Compare current HEAD with expected deploy commit.",
            "Check whether local files are modified.",
        ],
    ),

    Diagnostic(
        key="app_env",
        title="Inspect APP_ENV from .env in /var/www",
        patterns=[
            r"\bAPP_ENV\b",
            r"\.env",
            r"\benvironment\b",
            r"\bproduction\b",
            r"\bstaging\b",
        ],
        commands=[
            "cd /var/www/YOUR_APP",
            "grep '^APP_ENV=' .env",
            "grep '^APP_DEBUG=' .env",
            "php artisan env",
            "php artisan about",
            "php artisan config:show app.env",
        ],
        notes=[
            "If config is cached, .env changes may not reflect immediately.",
            "Check bootstrap/cache/config.php if Laravel config is cached.",
        ],
    ),

    Diagnostic(
        key="malware_cron",
        title="Detect malware or suspicious cron entries",
        patterns=[
            r"\bmalware\b",
            r"\bsuspicious\b",
            r"\bcron\b",
            r"\bcrontab\b",
            r"\bhacked\b",
            r"\binfected\b",
        ],
        commands=[
            "crontab -l",
            "sudo ls -lah /etc/cron.*",
            "sudo cat /etc/crontab",
            "sudo grep -R \"curl\\|wget\\|base64\\|bash\\|sh\" /etc/cron* /var/spool/cron/crontabs 2>/dev/null",
            "find /var/www -type f -mtime -3",
            "find /var/www -type f -name '*.php' -exec grep -Il \"eval\\|base64_decode\\|shell_exec\\|passthru\\|assert\" {} \\;",
        ],
        notes=[
            "Look for curl/wget piping into bash.",
            "Look for recently modified PHP files.",
            "Do not delete suspicious files immediately; copy them for evidence first.",
        ],
    ),

    Diagnostic(
        key="php_upload_limits",
        title="Debug PHP upload limits and timeout settings",
        patterns=[
            r"\bupload\b",
            r"\btimeout\b",
            r"\bphp.ini\b",
            r"\bpost_max_size\b",
            r"\bupload_max_filesize\b",
            r"\bmax_execution_time\b",
        ],
        commands=[
            "php -i | grep -E 'upload_max_filesize|post_max_size|max_execution_time|max_input_time|memory_limit'",
            "php --ini",
            "php -v",
            "grep -R \"upload_max_filesize\\|post_max_size\\|max_execution_time\" /etc/php/* -n 2>/dev/null",
            "sudo systemctl status php*-fpm",
            "sudo nginx -T | grep -E 'client_max_body_size|fastcgi_read_timeout'",
        ],
        notes=[
            "Effective upload size is limited by the smallest relevant limit.",
            "Check PHP-FPM config, web server config, and Laravel validation rules.",
            "Restart PHP-FPM after changing php.ini.",
        ],
    ),

    Diagnostic(
        key="laravel_cache_redis",
        title="Inspect Laravel cache/store driver health and Redis",
        patterns=[
            r"\bcache\b",
            r"\bredis\b",
            r"\bsession\b",
            r"\bstore\b",
            r"\bdriver\b",
        ],
        commands=[
            "cd /var/www/YOUR_APP",
            "grep -E 'CACHE_DRIVER|CACHE_STORE|SESSION_DRIVER|QUEUE_CONNECTION|REDIS_HOST|REDIS_PORT' .env",
            "php artisan tinker --execute=\"Cache::put('sysdiag_test', 'ok', 60); dump(Cache::get('sysdiag_test'));\"",
            "redis-cli ping",
            "redis-cli info server",
            "redis-cli info memory",
            "sudo systemctl status redis",
        ],
        notes=[
            "Expected Redis response is PONG.",
            "Check if Laravel uses database/file/redis cache store.",
            "If config is cached, run php artisan config:show or inspect cached config.",
        ],
    ),

    Diagnostic(
        key="disk_cleanup",
        title="Safely clean disk space without downtime",
        patterns=[
            r"\bdisk\b",
            r"\bspace\b",
            r"\bstorage\b",
            r"\bcleanup\b",
            r"\bclean\b",
            r"\bfull\b",
            r"\bno space\b",
        ],
        commands=[
            "df -h",
            "du -h --max-depth=1 /var/www 2>/dev/null | sort -h",
            "du -h --max-depth=1 /var/log 2>/dev/null | sort -h",
            "journalctl --disk-usage",
            "sudo find /var/log -type f -name '*.gz' -size +50M -ls",
            "sudo find /var/www -type f -name '*.log' -size +100M -ls",
            "php artisan queue:prune-failed --hours=168",
        ],
        notes=[
            "Do not delete active log files blindly.",
            "Prefer logrotate, journalctl vacuuming, old release cleanup, and Laravel failed-job pruning.",
            "Check backups before removing large archives.",
        ],
    ),

    Diagnostic(
        key="env_compare",
        title="Compare environment variables across servers",
        patterns=[
            r"\bcompare\b",
            r"\benv\b",
            r"\benvironment variables\b",
            r"\bservers\b",
            r"\bstaging\b",
            r"\bproduction\b",
        ],
        commands=[
            "cd /var/www/YOUR_APP",
            "grep -v '^#' .env | sort > /tmp/env.sorted",
            "ssh other-server 'cd /var/www/YOUR_APP && grep -v \"^#\" .env | sort' > /tmp/env.other.sorted",
            "diff -u /tmp/env.sorted /tmp/env.other.sorted",
        ],
        notes=[
            "Be careful not to paste secrets into logs or chat.",
            "Compare keys first before comparing values.",
            "Useful keys: APP_ENV, APP_DEBUG, DB_*, CACHE_*, QUEUE_*, REDIS_*, MAIL_*.",
        ],
    ),

    Diagnostic(
        key="laravel_queue",
        title="Inspect Laravel queue workers and failed jobs",
        patterns=[
            r"\bqueue\b",
            r"\bworker\b",
            r"\bfailed job\b",
            r"\bfailed_jobs\b",
            r"\bjob\b",
        ],
        commands=[
            "cd /var/www/YOUR_APP",
            "grep '^QUEUE_CONNECTION=' .env",
            "php artisan queue:failed",
            "php artisan queue:work --once -vvv",
            "ps aux | grep 'queue:work' | grep -v grep",
            "supervisorctl status",
            "sudo systemctl status supervisor",
        ],
        notes=[
            "Run queue:work --once to test one job safely.",
            "Check failed_jobs and worker process state.",
            "If using Redis queues, verify Redis health too.",
        ],
    ),

    Diagnostic(
        key="horizon_supervisor",
        title="Debug Laravel Horizon or Supervisor issues",
        patterns=[
            r"\bhorizon\b",
            r"\bsupervisor\b",
            r"\bsupervisorctl\b",
            r"\bdaemon\b",
        ],
        commands=[
            "cd /var/www/YOUR_APP",
            "php artisan horizon:status",
            "php artisan horizon:supervisors",
            "supervisorctl status",
            "sudo systemctl status supervisor",
            "sudo tail -n 100 /var/log/supervisor/supervisord.log",
            "ls -lah /etc/supervisor/conf.d/",
        ],
        notes=[
            "Horizon requires Redis.",
            "Supervisor may be running but the specific program may be stopped.",
            "After deploys, use php artisan horizon:terminate for graceful restart.",
        ],
    ),

    Diagnostic(
        key="failed_cron",
        title="Inspect failed cron jobs",
        patterns=[
            r"\bcron\b",
            r"\bschedule\b",
            r"\bscheduler\b",
            r"\bfailed cron\b",
            r"\bnot running\b",
        ],
        commands=[
            "crontab -l",
            "sudo grep CRON /var/log/syslog | tail -n 100",
            "sudo journalctl -u cron --since '1 hour ago'",
            "cd /var/www/YOUR_APP && php artisan schedule:list",
            "cd /var/www/YOUR_APP && php artisan schedule:run -vvv",
        ],
        notes=[
            "Laravel scheduler usually needs one cron entry running every minute.",
            "Check cron user, working directory, PHP path, and permissions.",
        ],
    ),

    Diagnostic(
        key="safe_restart",
        title="Restart Nginx, Apache, PHP-FPM, or MySQL safely",
        patterns=[
            r"\brestart\b",
            r"\breload\b",
            r"\bnginx\b",
            r"\bapache\b",
            r"\bphp-fpm\b",
            r"\bmysql\b",
            r"\bmariadb\b",
        ],
        commands=[
            "sudo nginx -t && sudo systemctl reload nginx",
            "sudo apachectl configtest && sudo systemctl reload apache2",
            "sudo systemctl status php*-fpm",
            "sudo systemctl reload php*-fpm",
            "sudo systemctl status mysql",
            "sudo systemctl status mariadb",
        ],
        notes=[
            "Prefer reload over restart when supported.",
            "Always test Nginx/Apache config before reloading.",
            "Be careful restarting MySQL on production.",
        ],
    ),
]


def score_diagnostic(text: str, diagnostic: Diagnostic) -> int:
    score = 0
    for pattern in diagnostic.patterns:
        if re.search(pattern, text, re.IGNORECASE):
            score += 1
    return score


def detect(text: str) -> list[tuple[int, Diagnostic]]:
    results = []

    for diagnostic in DIAGNOSTICS:
        score = score_diagnostic(text, diagnostic)
        if score > 0:
            results.append((score, diagnostic))

    return sorted(results, key=lambda item: item[0], reverse=True)


def print_diagnostic(score: int, diagnostic: Diagnostic) -> None:
    print("=" * 72)
    print(f"Detected: {diagnostic.title}")
    print(f"Key: {diagnostic.key}")
    print(f"Confidence score: {score}")
    print()

    print("Commands to inspect:")
    for command in diagnostic.commands:
        print(f"  - {command}")

    print()
    print("What to look for:")
    for note in diagnostic.notes:
        print(f"  - {note}")

    print()


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage:")
        print('  python sysdiag.py "Laravel queue is not processing jobs"')
        sys.exit(1)

    text = " ".join(sys.argv[1:])
    matches = detect(text)

    if not matches:
        print("No exact diagnostic matched.")
        print("Try mentioning git, APP_ENV, cron, upload, Redis, disk, queue, Horizon, Supervisor, Nginx, Apache, PHP-FPM, or MySQL.")
        sys.exit(0)

    for score, diagnostic in matches[:3]:
        print_diagnostic(score, diagnostic)


if __name__ == "__main__":
    main()
