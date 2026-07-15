import os
import re
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from app.models.author import Author
from app.models.collection import Collection
from app.models.poem import Poem


class Command(BaseCommand):
    help = "Импорт стихов и сборников из MySQL дампа .data/poethrenoff.sql"

    def handle(self, *args, **options):
        sql_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            ),
            ".data",
            "poethrenoff.sql",
        )

        if not os.path.exists(sql_path):
            self.stdout.write(self.style.ERROR(f"Файл дампа не найден: {sql_path}"))
            return

        author = Author.objects.get(pk=1)

        work_group_pattern = re.compile(
            r"^\((\d+),\s*66,\s*'((?:[^'\\]|\\.)*)',\s*'((?:[^'\\]|\\.)*)',\s*(-?\d+),\s*(\d+)\)[,;]?$"
        )
        work_pattern = re.compile(
            r"^\((\d+),\s*(\d+),\s*'((?:[^'\\]|\\.)*)',\s*'((?:[^'\\]|\\.)*)',\s*'((?:[^'\\]|\\.)*)',\s*(\d+),\s*(\d+)\)[,;]?$"
        )

        target_groups = []
        works_by_group = defaultdict(list)

        in_work_group_insert = False
        in_work_insert = False

        with open(sql_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                if "INSERT INTO `work_group`" in line:
                    in_work_group_insert = True
                    in_work_insert = False
                    continue

                if "INSERT INTO `work`" in line:
                    in_work_group_insert = False
                    in_work_insert = True
                    continue

                if line.startswith("--") or line.startswith("/*"):
                    continue

                if in_work_group_insert:
                    m = work_group_pattern.match(line)
                    if m:
                        group_id = int(m.group(1))
                        title = m.group(2).replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
                        comment = m.group(3).replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
                        group_order = int(m.group(4))
                        group_active = int(m.group(5))
                        target_groups.append(
                            {
                                "id": group_id,
                                "title": title,
                                "comment": comment,
                                "order": group_order,
                                "active": bool(group_active),
                            }
                        )

                if in_work_insert:
                    m = work_pattern.match(line)
                    if m:
                        work_id = int(m.group(1))
                        work_group = int(m.group(2))
                        title = m.group(3).replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
                        text = (
                            m.group(4)
                            .replace("\\r\\n", "\n")
                            .replace("\\n", "\n")
                            .replace('\\"', '"')
                            .replace("\\'", "'")
                            .replace("\\\\", "\\")
                        )
                        comment = m.group(5).replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
                        work_order = int(m.group(6))
                        work_active = int(m.group(7))
                        works_by_group[work_group].append(
                            {
                                "id": work_id,
                                "title": title,
                                "text": text,
                                "comment": comment,
                                "order": work_order,
                                "active": bool(work_active),
                            }
                        )

        target_groups.sort(key=lambda g: g["order"], reverse=True)

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("TRUNCATE TABLE app_poem, app_collection RESTART IDENTITY")

            group_map = {}
            for idx, group in enumerate(target_groups, start=1):
                collection = Collection.objects.create(
                    author=author,
                    title=group["title"],
                    comment=group["comment"],
                    position=idx,
                    active=group["active"],
                )
                group_map[group["id"]] = collection

            for group in target_groups:
                works = sorted(works_by_group.get(group["id"], []), key=lambda w: w["order"])
                collection = group_map[group["id"]]
                for idx, work in enumerate(works, start=1):
                    Poem.objects.create(
                        author=author,
                        collection=collection,
                        title=work["title"],
                        content=work["text"],
                        comment=work["comment"],
                        position=idx,
                        active=work["active"],
                    )
                self.stdout.write(self.style.SUCCESS(f"Импортировано стихов в '{collection.title}': {len(works)}"))

        self.stdout.write(self.style.SUCCESS("Импорт завершен."))
