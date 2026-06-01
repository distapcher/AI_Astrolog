from aiogram import Router

from bot.handlers.chart import router as chart_router
from bot.handlers.common import router as common_router

router = Router()
router.include_router(common_router)
router.include_router(chart_router)
