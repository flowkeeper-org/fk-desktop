import asyncio

from PySide6.QtWidgets import QTabWidget, QLabel
from assertpy import assert_that

from fk.e2e.e2e_test import E2eTest


async def test_backlog_loaded(t: E2eTest):
    print('Entered test')
    w = t.window()
    print(f'Main window: {w}')
    await asyncio.sleep(1)
    tabs = w.findChild(QTabWidget, "tabs")
    tabs.setCurrentIndex(2)
    await asyncio.sleep(1)
    t.mouse_click(w.findChild(QLabel, "linkWebsite"))
    await asyncio.sleep(1)
    assert_that(tabs.currentIndex()).is_equal_to(1)
