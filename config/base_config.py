# Desc: base config
PLATFORM = "xhs"
KEYWORDS = "健身,旅游"
LOGIN_TYPE = "qrcode"  # qrcode or phone or cookies
LOGIN_TYPE_COOKIE = "cookies"  # qrcode or phone or cookies
# If it's on the Xiaohongshu platform, only the web_session cookie will be kept.
# xhs cookie format -> web_session=040069b2acxxxxxxxxxxxxxxxxxxxx;
# COOKIES = "web_session=030037a3824fcc373b5ef45dc9234a4ebc975f;"
COOKIES = "web_session=030037a38ed7cb378c09f3c5c5234a27c6c94c;"
# COOKIES = "web_session=030037a38976af3724359764c2234ac9d51e5c;"

# redis config
REDIS_DB_HOST = "redis://127.0.0.1"  # your redis host
REDIS_DB_PWD = "123456"  # your redis password

# enable ip proxy
# ENABLE_IP_PROXY = True
ENABLE_IP_PROXY = False

# retry_interval
RETRY_INTERVAL = 60 * 30  # 30 minutes

# playwright headless
HEADLESS = True

# save login state
SAVE_LOGIN_STATE = False

# save user data dir
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# max page num
MAX_PAGE_NUM = 20

# max concurrency num
MAX_CONCURRENCY_NUM = 10
