from typing import Any, Dict, List, Tuple

from app.plugins import _PluginBase
from app.helper.downloader import DownloaderHelper
from app.core.event import eventmanager, Event
from app.schemas.types import EventType
from app.log import logger


class TorrentTagsSetter(_PluginBase):
    # 插件名称
    plugin_name = "种子标签管理"
    # 插件描述
    plugin_desc = "在特定事件发生时为种子添加特定 tags"
    # 插件图标
    plugin_icon = "torrent.png"
    # 主题色
    plugin_color = "#C9221B"
    # 插件版本
    plugin_version = "1.0"
    # 插件作者
    plugin_author = "WithdewHua"
    # 作者主页
    author_url = "https://github.com/WithdewHua"
    # 插件配置项ID前缀
    plugin_config_prefix = "torrenttagssetter_"
    # 加载顺序
    plugin_order = 99
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _qb = None
    _tr = None
    _enabled = False
    _add_tmdb_id = False
    _tmdb_id_prefix = ''

    def init_plugin(self, config: dict = None):
        self.download_helper = DownloaderHelper()
        if config:
            self._enabled = config.get("enabled")
            self._add_tmdb_id = config.get("add_tmdb_id")
            self._tmdb_id_prefix = config.get('tmdb_id_prefix')

    def get_state(self) -> bool:
        return self._enabled
    
    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        return [
            {
                "component": "VForm",
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    # 'md': 6
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
                                    # 'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'add_tmdb_id',
                                            'label': '添加 TMDB ID',
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
                                    # 'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'tmdb_id_prefix',
                                            'label': '添加 TMDB ID 时增加前缀',
                                            'placeholder': ''
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            'enabled': False,
            'add_tmdb_id': False,
            'tmdb_id_prefix': '',
        }

    def get_page(self) -> List[dict]:
        pass

    @eventmanager.register(EventType.DownloadAdded)
    def set_tag_after_downloadadded(self, event: Event):
        """
        种子下载事件
        """
        if not self.get_state() or not event.event_data:
            return
        
        torrent_hash = event.event_data.get("hash")
        context = event.event_data.get("context")
        downloader = event.event_data.get("downloader")
        service = self.download_helper.get_service(downloader)
        downloader_obj = service.instance
        if not service or not downloader_obj:
            logger.error(f"未获取到下载器：{downloader}")
            return
        if downloader_obj.is_inactive():
            logger.error(f"下载器 {downloader} 不在线")
            return

        media_info = context.media_info
        if not media_info:
            logger.info("媒体信息不存在，不做处理")
            return
        try:
            if not self._add_tmdb_id:
                return
            if not media_info.tmdb_id:
                logger.error(f"未获取到媒体 {media_info.title} 的 tmdb id 信息")
            tag = self._tmdb_id_prefix + str(media_info.tmdb_id)
            if service.type == "qbittorrent":
                downloader_obj.set_torrents_tag(ids=torrent_hash, tags=tag)
            if service.type == "transmission":
                # 由于 tr 会覆盖原标签，此处设置追加
                _tags = downloader_obj.get_torrent_tags(ids=torrent_hash)
                downloader_obj.set_torrent_tag(ids=torrent_hash, tags=tag, org_tags=_tags)
        except Exception as e:
            logger.error(f"设置种子标签失败：{e}")

    def stop_service(self):
        pass