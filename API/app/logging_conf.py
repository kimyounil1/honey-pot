# app/logging_conf.py
from logging.config import dictConfig

def setup_logging(log_path: str = "/src/app/log"):
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,

        # 공통 포맷터
        "formatters": {
            "plain": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
            "jsonlike": {
                "format": '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":%(message)s}'
            },
        },

        # 핸들러: 전용 파일 로거(로그 로테이션)
        "handlers": {
            "debug_body_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": f"{log_path}/debug_body.log",
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8",
                "level": "INFO",
                "formatter": "plain",
            },
            # 필요 시 앱 전체 로그(별도 파일)
            "app_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": f"{log_path}/app.log",
                "maxBytes": 20 * 1024 * 1024,
                "backupCount": 3,
                "encoding": "utf-8",
                "level": "INFO",
                "formatter": "plain",
            },
            # 콘솔(개발용)
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "plain",
            },
        },

        # 로거
        "loggers": {
            # 여기에 우리가 사용할 "전용 바디 로거"를 정의
            "debug.body": {
                "handlers": ["debug_body_file"],
                "level": "INFO",
                "propagate": False,  # 상위(루트)로 전파 막기 → 다른 로그와 섞이지 않음
            },
            # SQLAlchemy 시끄러우면 레벨 낮추기
            "sqlalchemy.engine": {
                "handlers": ["app_file"],   # 또는 "console"
                "level": "WARNING",         # INFO/DEBUG이면 너무 많음
                "propagate": False,
            },
        },

        # 루트 로거(원하면)
        "root": {
            "handlers": ["console", "app_file"],
            "level": "INFO",
        },
    })
