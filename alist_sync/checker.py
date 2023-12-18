from pathlib import PurePosixPath

from alist_sdk import Item
from pydantic import BaseModel

from alist_sync.scanner import Scanner


class Checker(BaseModel):
    # matrix: 相对文件路径 -> {同步目录: Item}
    matrix: dict[PurePosixPath, dict[PurePosixPath, Item]]
    # cols: 同步目录 - base_path
    cols: list[PurePosixPath]

    @classmethod
    def checker(cls, scanner: Scanner):
        _result = {}
        for base_path, items in scanner.items.items():
            items: list[Item]
            base_path: str | PurePosixPath
            for item in items:
                r_path = item.full_name.relative_to(base_path)
                try:
                    _result[PurePosixPath(r_path)].setdefault(
                        PurePosixPath(base_path), item
                    )
                except KeyError:
                    _result[PurePosixPath(r_path)] = {PurePosixPath(base_path): item}

        return cls(
            matrix=_result, cols=[PurePosixPath(t) for t in scanner.items.keys()]
        )

    def model_dump_table(self):
        """"""
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column(
            "r_path",
            style="dim red",
        )
        for col in self.cols:
            table.add_column(str(col), justify="center", vertical="middle")

        for r_path, raw in self.matrix.items():
            table.add_row(
                str(r_path), *["True" if raw.get(tt) else "False" for tt in self.cols]
            )
        console.print(table)


if __name__ == "__main__":
    import json
    from pathlib import Path

    checker = Checker.checker(
        *[
            ScannedDir(**s)
            for s in json.load(
                Path(__file__)
                .parent.parent.joinpath("tests/resource/SyncDirs-m.json")
                .open()
            )
        ]
    )
    checker.model_dump_table()
