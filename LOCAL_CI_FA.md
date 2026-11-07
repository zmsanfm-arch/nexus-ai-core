# اجرای CI محلی NEXUS بدون مصرف سهمیه GitHub Actions

این مسیر برای زمانی است که GitHub-hosted runner در دسترس نیست. اجرای آن از Docker روی سیستم خودتان استفاده می‌کند و هیچ GitHub Actions minute مصرف نمی‌کند.

## اجرا

در ریشه مخزن:
```bash
bash scripts/run_local_ci_docker.sh
```

این اسکریپت به‌ترتیب:
1. دسترسی Docker daemon را بررسی می‌کند.
2. یک شبکه Docker مجزا و PostgreSQL 16 موقت می‌سازد.
3. محیط Python 3.12، وابستگی‌های تست، pip-audit، Bandit و Playwright Chromium را build می‌کند.
4. pytest، بررسی آسیب‌پذیری وابستگی‌ها، Bandit و تست مرورگر را اجرا می‌کند.
5. Docker image اصلی برنامه را build و health-check می‌کند.
6. کانتینرها و شبکه موقت را در پایان پاک می‌کند.

## نیازمندی‌ها

- Docker Engine/ Desktop فعال و دسترسی کاربر به Docker daemon
- اتصال اینترنت برای دریافت imageها و بسته‌ها در اولین اجرا
- فضای دیسک کافی برای imageهای Python، PostgreSQL و Chromium

## تنظیمات اختیاری

```bash
NEXUS_CI_APP_PORT=18081 bash scripts/run_local_ci_docker.sh
NEXUS_CI_PG_PASSWORD='local-test-only' bash scripts/run_local_ci_docker.sh
```

## نکته مهم

این اسکریپت آزمون backup/restore رمزنگاری‌شده‌ای را که در workflow ابری تعریف شده اجرا نمی‌کند. همچنین ایجاد این فایل‌ها به‌معنای موفق بودن تست‌ها نیست؛ فقط پس از اجرای کامل و خروج با کد صفر می‌توان نتیجه را سبز اعلام کرد.
