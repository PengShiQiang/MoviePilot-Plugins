import datetime
import threading
import time
from mailcap import lookup

import pytz
from typing import Optional, List, Tuple, Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.chain.subscribe import SubscribeChain
from app.schemas import Subscribe as SubscribeSchema

from app.db import get_db

from app.plugins import _PluginBase


from app.log import logger
from app.core.config import settings
from app.db.models.subscribe import Subscribe

from fastapi import Depends
from sqlalchemy.orm import Session


class SearchSubscribe(_PluginBase):


    # 插件名称
    plugin_name = "手动订阅搜索"
    # 插件描述
    plugin_desc = "手动执行所有订阅的搜索"
    # 插件图标
    plugin_icon = ""
    # 插件版本
    plugin_version = "1.0"
    # 插件作者
    plugin_author = "PengShiQiang"
    # 作者主页
    author_url = "https://github.com/PengShiQiang"
    # 插件配置项ID前缀
    plugin_config_prefix = "searchsubscribe_"
    # 加载顺序
    plugin_order = 0
    # 可使用的用户级别
    auth_level = 2

    # 退出事件
    _event = threading.Event()

    _scheduler = None
    _enabled = False
    _onlyonce = False
    _cron = None

    def init_plugin(self, config: dict = None):

        if config:
            self._enabled = config.get("enabled")
            self._onlyonce = config.get("onlyonce")
            self._cron = config.get("cron")

        # 停止现有任务
        self.stop_service()

        # 启动服务
        if self._onlyonce:
            self._scheduler = BackgroundScheduler(timezone=settings.TZ)
            self._scheduler.add_job(func=self.search, trigger='date',
                                    run_date=datetime.datetime.now(
                                        tz=pytz.timezone(settings.TZ)) + datetime.timedelta(seconds=3)
                                    )
            logger.info(f"手动订阅搜索服务启动，立即运行一次")
            # 关闭一次性开关
            self._onlyonce = False
            # 保存配置
            self.__update_config()
            # 启动服务
            if self._scheduler.get_jobs():
                self._scheduler.print_jobs()
                self._scheduler.start()

    def __update_config(self):
        """
        更新配置
        """
        self.update_config({
            "enabled": self._enabled,
            "onlyonce": self._onlyonce,
            "cron": self._cron
        })

    def get_page(self) -> Optional[List[dict]]:
        pass

    def get_state(self) -> bool:
        return self._enabled

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册插件公共服务
        [{
            "id": "服务ID",
            "name": "服务名称",
            "trigger": "触发器：cron/interval/date/CronTrigger.from_crontab()",
            "func": self.xxx,
            "kwargs": {} # 定时器参数
        }]
        """
        if self._enabled and self._cron:
            return [{
                "id": "SearchSubscribe_",
                "name": "手动订阅搜索服务",
                "trigger": CronTrigger.from_crontab(self._cron),
                "func": self.search,
                "kwargs": {}
            }]


    def get_form(self) -> Tuple[Optional[List[dict]], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """

        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'onlyonce',
                                            'label': '立即运行一次',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VCronField',
                                        'props': {
                                            'model': 'cron',
                                            'label': '定时搜索周期',
                                            'placeholder': '5位cron表达式'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "onlyonce": False,
            "cron": ""
        }



    def search(self, db: Session = Depends(get_db)):
        """
        依次给现有的订阅执行搜索
        """

        subs = Subscribe.list(db)
        dict_list = [SubscribeSchema.from_orm(sub).dict() for sub in subs]
        if dict_list:
            logger.info(f"检测到你有以下订阅{[dict_id['name'] for dict_id in dict_list]}")
        else:
            logger.info(f"你还没有订阅！")
            return
        sub_id = [dict_id['id'] for dict_id in dict_list]

        sub_chain = SubscribeChain()
        for sub in sub_id:
            sub_chain.search(None, 'R', True)
            time.sleep(120)
        logger.info("所有订阅手动执行搜索成功")


    def stop_service(self):
        """
        退出插件
        """
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            logger.error("退出插件失败：%s" % str(e))
