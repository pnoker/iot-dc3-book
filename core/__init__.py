"""core 包 - 核心基础设施"""

from core.log import get_logger, setup_logging
from core.state import BookState

__all__ = ["BookState", "get_logger", "setup_logging"]
