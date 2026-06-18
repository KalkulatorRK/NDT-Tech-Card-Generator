"""
Registry of all implemented normative document data modules.

``populate_standards()`` is called once on app startup to ensure
NDTMethod and NormativeDocument records exist in the database.
"""

REGISTRY = [
    {
        "method_code": "VT",
        "method_name": "Визуальный и измерительный (ВИК)",
        "documents": [
            {
                "code": "РД 03-606-03",
                "name": "Инструкция по визуальному и измерительному контролю",
                "short_name": "РД 03-606-03 (ВИК)",
                "data_module": "ndt_data.rd_03_606_03",
                "version": "2003",
                "has_card_template": True,
                "has_quality_criteria": True,
            },
            {
                "code": "ГОСТ Р ИСО 17637-2014",
                "name": "Неразрушающий контроль сварных соединений. Визуальный контроль.",
                "short_name": "ГОСТ Р ИСО 17637",
                "data_module": "ndt_data.gost_r_iso_17637",
                "version": "2014",
                "has_card_template": True,
                "has_quality_criteria": True,
            },
        ],
    },
    {
        "method_code": "RT",
        "method_name": "Радиографический (РК)",
        "documents": [
            {
                "code": "ГОСТ 7512-82",
                "name": "Контроль неразрушающий. Соединения сварные. Радиографический метод.",
                "short_name": "ГОСТ 7512",
                "data_module": "ndt_data.gost_7512",
                "version": "1982",
                "has_card_template": True,
                "has_quality_criteria": True,
            },
            {
                "code": "НП-105-18",
                "name": "Правила контроля металла оборудования и трубопроводов атомных энергетических установок при изготовлении и монтаже",
                "short_name": "НП-105-18",
                "data_module": "ndt_data.np_105_18",
                "version": "2018",
                "has_card_template": True,
                "has_quality_criteria": True,
            },
        ],
    },
    {
        "method_code": "PT",
        "method_name": "Капиллярный (ПВК)",
        "documents": [
            {
                "code": "ГОСТ Р ИСО 3452-1-2011",
                "name": "Неразрушающий контроль. Капиллярный контроль. Часть 1. Основные требования.",
                "short_name": "ГОСТ Р ИСО 3452-1",
                "data_module": "ndt_data.gost_r_iso_3452",
                "version": "2011",
                "has_card_template": True,
                "has_quality_criteria": True,
            },
        ],
    },
    {
        "method_code": "LT",
        "method_name": "Контроль герметичности (КГ)",
        "documents": [
            {
                "code": "ГОСТ Р 52005-2003",
                "name": "Контроль неразрушающий. Метод течеискания. Общие требования.",
                "short_name": "ГОСТ Р 52005",
                "data_module": "ndt_data.gost_r_52005",
                "version": "2003",
                "has_card_template": True,
                "has_quality_criteria": True,
            },
        ],
    },
]


def populate_standards():
    """
    Idempotently create NDTMethod and NormativeDocument records
    for all entries in REGISTRY.
    """
    from apps.standards.models import NDTMethod, NormativeDocument

    for entry in REGISTRY:
        method, _ = NDTMethod.objects.get_or_create(
            code=entry["method_code"],
            defaults={"name": entry["method_name"]},
        )
        for doc_def in entry["documents"]:
            NormativeDocument.objects.update_or_create(
                code=doc_def["code"],
                defaults={
                    "method": method,
                    "name": doc_def["name"],
                    "short_name": doc_def["short_name"],
                    "data_module": doc_def["data_module"],
                    "version": doc_def["version"],
                    "has_card_template": doc_def["has_card_template"],
                    "has_quality_criteria": doc_def["has_quality_criteria"],
                },
            )
