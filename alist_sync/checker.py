from alist_sdk import Item
from alist_sync.models import SyncDir


class Checker:
    """检查结果"""

    def __init__(self, *scanned_dirs: SyncDir):
        self._result: dict[str, dict[str, Item]] = dict()
        self.table_title = [t.base_path for t in scanned_dirs]
        for scanned_dir in scanned_dirs:
            self.check(scanned_dir)

    @property
    def result(self):
        return self._result

    def check(self, scanned_dir: SyncDir):
        for item in scanned_dir.items:
            r_path = item.full_name.relative_to(
                scanned_dir.base_path
            )
            try:
                self._result[str(r_path)].setdefault(scanned_dir.base_path, item)
            except KeyError:
                self._result[str(r_path)] = {scanned_dir.base_path: item}

    def rich_table(self):
        """Rich的报表  """
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column('r_path', style="dim red", width=120)
        for col in self.table_title:
            table.add_column(col, justify="center", vertical='middle')

        for r_path, raw in self._result.items():
            table.add_row(
                r_path,
                *[True if raw.get(tt) else "False" for tt in self.table_title]
            )
        console.print(table)


if __name__ == '__main__':
    import json
    from pathlib import Path

    checker = Checker(*[SyncDir(**s) for s in json.load(
        Path(__file__).parent.parent.joinpath('tests/resource/SyncDirs.json').open())
                        ])
    checker.rich_table()
