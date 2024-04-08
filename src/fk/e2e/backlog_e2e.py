import asyncio

from PySide6.QtWidgets import QApplication
from assertpy import assert_that

from fk.e2e.abstract_e2e_test import AbstractE2eTest
from fk.qt.backlog_tableview import BacklogTableView


class BacklogE2eTest(AbstractE2eTest):
    def __init__(self, app: QApplication):
        super().__init__(app)

    def custom_settings(self) -> dict[str, str]:
        return {
            'FileEventSource.filename': './backlog-e2e.txt',
            'Application.show_tutorial': 'False',
        }

    async def test_backlog_loaded(self):
        print('DEBUG: Entered test')
        await asyncio.sleep(0.5)

        w = self.window()
        print(f'DEBUG: Main window: {w}')
        assert_that(w.windowTitle()).is_equal_to('Flowkeeper')

        table: BacklogTableView = w.findChild(BacklogTableView, "backlogs_table")
        print(f'DEBUG: Table: {table}')
        model = table.model()
        count = model.rowCount()
        print(f'DEBUG: Rows: {count}')
        assert_that(count).is_equal_to(10)
        assert_that(model.index(0, 0).data()).is_equal_to('2024-03-31, Sunday')
        assert_that(model.index(1, 0).data()).is_equal_to('27/10/23')
        assert_that(model.index(2, 0).data()).is_equal_to('Flowkeeper')

        self.mouse_click_row(table, 6)
        print(f'DEBUG: Clicked on a random backlog')

        await asyncio.sleep(0.1)
        #t.keypress(Qt.Key.Key_N, True)
        #print('DEBUG: Typed')
        self.get_focused()
        #await asyncio.sleep(0.1)
        #t.keypress(Qt.Key.Key_Enter)
