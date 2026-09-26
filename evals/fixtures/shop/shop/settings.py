SECRET_KEY = "dev-only"
INSTALLED_APPS = ["django.contrib.auth", "django.contrib.contenttypes", "shop"]
ROOT_URLCONF = "shop.urls"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "shop.sqlite3"}}
