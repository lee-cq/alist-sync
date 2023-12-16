from pathlib import PurePosixPath
from pydantic import BaseModel

from alist_sdk import Item


class Checker(BaseModel):
    # matrix: 相对文件路径 -> {同步目录: Item}
    matrix: dict[PurePosixPath, dict[PurePosixPath, Item]]
    # cols: 同步目录 - base_path
    cols: list[PurePosixPath]

    @classmethod
    def checker(cls, *scanned_dirs):
        _result = {}
        for scanned_dir in scanned_dirs:
            for item in scanned_dir.items:
                r_path = item.full_name.relative_to(
                    scanned_dir.base_path
                )
                try:
                    _result[PurePosixPath(r_path)].setdefault(
                        PurePosixPath(scanned_dir.base_path),
                        item
                    )
                except KeyError:
                    _result[PurePosixPath(r_path)] = {
                        PurePosixPath(scanned_dir.base_path): item
                    }

        return cls(
            matrix=_result,
            cols=[PurePosixPath(t.base_path) for t in scanned_dirs]
        )

    def model_dump_table(self):
        """"""
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column('r_path', style="dim red", )
        for col in self.cols:
            table.add_column(str(col), justify="center", vertical='middle')

        for r_path, raw in self.matrix.items():
            table.add_row(
                str(r_path),
                *["True" if raw.get(tt) else "False" for tt in self.cols]
            )
        console.print(table)


if __name__ == '__main__':
    import json
    from pathlib import Path
    from alist_sync.models import SyncDir

    checker = Checker.checker(*[SyncDir(**s) for s in json.load(
        Path(__file__).parent.parent.joinpath('tests/resource/SyncDirs-m.json').open())
                                ])
    checker.model_dump_table()
