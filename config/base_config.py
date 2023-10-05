# Desc: base config
PLATFORM = "xhs"
KEYWORDS = "python,golang"
LOGIN_TYPE = "qrcode"  # qrcode or phone or cookies
LOGIN_TYPE_COOKIE = "cookie"  # qrcode or phone or cookies
COOKIES = "web_session=030037a3824fcc373b5ef45dc9234a4ebc975f;"
# enable ip proxy
ENABLE_IP_PROXY = False

# retry_interval
RETRY_INTERVAL = 60 * 30  # 30 minutes

# playwright headless
HEADLESS = True

# save login state
SAVE_LOGIN_STATE = True

# save user data dir
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# crawler max notes count
CRAWLER_MAX_NOTES_COUNT = 20

# max concurrency num
MAX_CONCURRENCY_NUM = 10
