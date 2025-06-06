import time
import datetime
import os
import tempfile
import pathlib
import kontur.pie as pie
import subprocess


def _env(env_name, default = ''):
    return pie.os.environ.get(env_name, default)


API_KEY = _env("API_KEY")
UPDSERVICE_LOCATION = _env("UPDSERVICE_LOCATION", "https://update.kontur.ru")
DISABLE_FLAGS_EPF = "КЭДО_АвтоматическоеСнятиеГалочекРасширения"
INSTALL_STAGE_EPF = 'КЭДО_УстановитьАльтернативноеАпи'
SAVE_HASH_EPF = "КЭДО_СохранитьХешСуммуРасширения"


def start():
    ib = pie.helpers.current_ib()
    ib.open_designer()


# Выгрузка


def dump(custom_path=None):
    pie.dump_ext(ext_map={"УправлениеПортфелями83": "src"}, ib=_ib(custom_path))
    ext_src = pie.src.ExtSrc("src", copy=False)
    versioning.clear_version_info(ext_src)


def dump_zup(custom_path=None):
    pie.dump_ext(ext_map={"КЭДО": "src/kedo_zup"}, ib=_ib_zup(custom_path))
    ext_src = pie.src.ExtSrc("src/kedo_zup", copy=False)
    versioning.clear_version_info(ext_src)


def dump_erp():
    pie.dump_ext(ext_map={"КЭДО": "src/kedo_erp"}, ib=_ib_erp())


def dump_upp():
    pie.dump_epf(
        epf="ordinaryForms/build/kedo_upp.epf",
        epf_xml="ordinaryForms/src/kedo_upp/kedo_upp.xml",
        ib=_ib_upp(),
    )


def dump_test():
    pie.dump_ext(ext_map={"КЭДОТестирование": "src/kedo_test"}, ib=_ib_zup())


# Загрузка


#def load():
#    pie.load_ext(ext_list=["src"], update=False, ib=_ib())
def load(custom_path=None, to_update=False):
    #version_info = versioning.git_version()

    with pie.src.ExtSrc("src") as ext_src:
        #versioning.set_version_info(ext_src, version_info)
        pie.load_ext(ext_list=[str(ext_src)], update=to_update, ib=_ib_zup(custom_path))

def load_zup(custom_path=None, to_update=False):
    version_info = versioning.git_version()

    with pie.src.ExtSrc("src/kedo_zup") as ext_src:
        versioning.set_version_info(ext_src, version_info)
        pie.load_ext(ext_list=[str(ext_src)], update=to_update, ib=_ib_zup(custom_path))


def load_zup(custom_path=None, to_update=False):
    version_info = versioning.git_version()

    with pie.src.ExtSrc("src/kedo_zup") as ext_src:
        versioning.set_version_info(ext_src, version_info)
        pie.load_ext(ext_list=[str(ext_src)], update=to_update, ib=_ib_zup(custom_path))


def load_erp():
    pie.load_ext(ext_list=["src/kedo_erp"], update=False, ib=_ib_erp())


def load_test():
    pie.load_ext(ext_list=["src/kedo_test"], update=False, ib=_ib_zup())


# Сборка

def generate_md_duplicate(result, branch_name = '', project_url = ''):

    md_content = "# Отчет о дубликатах ID\n\n"

    for file_path, duplicates_by_category in result:
        # Формируем ссылку на файл в ветке
        formatted_file_path = file_path.replace('\\', '/')
        file_link = f"{project_url}/-/blob/{branch_name}/{formatted_file_path}"

        md_content += f"## Файл: [{formatted_file_path}]({file_link})\n"

        for category, values in duplicates_by_category.items():
            duplicates = values['Дубликаты']
            if duplicates:
                md_content += f"### Категория: {category}\n"
                for elem_id, occurrences in duplicates.items():
                    md_content += f"- **ID**: `{elem_id}` найдено {len(occurrences)} раз(а)\n"
                    for occ in occurrences:
                        name = occ['attributes'].get('name', 'Без имени')
                        md_content += f"  - {name}\n"
                md_content += "\n"

    return md_content

def note_gitlab(md_text, project_id, commit_ref_name, py_lint_token):

    import requests

    """
    Отправляет комментарий с отчетом о дубликатах в Merge Request.
    """
    # URL для получения Merge Request ID
    mr_url = f"https://git.skbkontur.ru/api/v4/projects/{project_id}/merge_requests?source_branch={commit_ref_name}"
    
    # Заголовки для авторизации
    headers = {"PRIVATE-TOKEN": py_lint_token}
    
    # Получаем ID Merge Request
    response = requests.get(mr_url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Error fetching merge request: {response.text}")
    
    mr_data = response.json()
    if not mr_data:
        raise Exception(f"No merge request found for branch {commit_ref_name}")
    
    MR_ID = mr_data[0]['iid']
    print(f"Merge Request ID: {MR_ID}")
    
    # Формируем тело комментария
    comment_data = {"body": md_text}
    
    # URL для отправки комментария
    comment_url = f"https://git.skbkontur.ru/api/v4/projects/{project_id}/merge_requests/{MR_ID}/discussions"
    
    # Отправляем комментарий через POST запрос
    response = requests.post(comment_url, headers={**headers, "Content-Type": "application/json"}, json=comment_data)
    
    if response.status_code != 201:
        raise Exception(f"Error posting comment: {response.text}")

def check_duplicate(src = 'src/kedo_zup'):
    
    result = duplicate_ids.check_all_form_xml_in_src(src)
    
    if result:
        CI_PROJECT_ID = _env("CI_PROJECT_ID")
        CI_COMMIT_REF_NAME = _env("CI_COMMIT_REF_NAME")
        PY_LINT_TOKEN = _env("PY_LINT_TOKEN")
        CI_PROJECT_URL = _env("CI_PROJECT_URL")

        md_text = generate_md_duplicate(result, CI_COMMIT_REF_NAME, CI_PROJECT_URL)
        
        if CI_PROJECT_ID and CI_COMMIT_REF_NAME and PY_LINT_TOKEN:
            note_gitlab(md_text, CI_PROJECT_ID, CI_COMMIT_REF_NAME, PY_LINT_TOKEN)
            raise Exception(f"Error: {md_text}")
        else:
            raise Exception(f"Error: {md_text}")

def build():
    target = pie.os.environ["KEDO_SRC"]

    ib = _base()
    if target == "kedo_upp":
        pie.build_epf(
            epf="build/kedo_upp.epf",
            epf_xml="src/kedo_upp/kedo_upp.xml",
            ib=ib,
        )
    else:
        build_zup_bundle(target)

    check_duplicate('src/kedo_zup')



def build_zup():
    ib = _ib_zup()
    version_info = versioning.git_version()
    with pie.src.ExtSrc("src/kedo_zup") as ext_src:
        versioning.set_version_info(ext_src, version_info)
        ib.load_ext(ext_name="КЭДО", ext_src=str(ext_src))
    ib.dump_cfe(ext_name="КЭДО", cfe="build/kedo_zup.cfe")

    check_duplicate("src/kedo_zup")


def build():
    ib = _ib_bp3()
    ib.load_ext(ext_name="КЭДО", ext_src="src")
    ib.dump_cfe(ext_name="КЭДО", cfe="build/up83.cfe")

    check_duplicate("src/kedo_bp3")


def build_erp():
    ib = _ib_erp()
    ib.load_ext(ext_name="КЭДО", ext_src="src/kedo_erp")
    ib.dump_cfe(ext_name="КЭДО", cfe="build/kedo_erp.cfe")

    check_duplicate("src/kedo_erp")


def build_upp():
    pie.build_epf(
        epf="ordinaryForms/build/kedo_upp.epf",
        epf_xml="ordinaryForms/src/kedo_upp/kedo_upp.xml",
        ib=_ib_upp(),
    )


def build_zup_bundle(target=None):
    if target is None:
        target = "kedo_zup"
    PRODUCT = "КЭДО"
    SYNONYM = "Контур.КЭДО - обработка обновления"
    SERVICE = target

    version_info = versioning.git_version()
    version = version_info.version
    version_info.dump(f"build/{target}_version_info.json")

    # extension
    ib = _base()
    with pie.src.ExtSrc(src=f"src/{target}") as src:
        versioning.set_version_info(src, version_info)
        ib.load_ext(ext_src=str(src), ext_name=PRODUCT, update=True)
    checksum_filename = _checksum_filename(target)
    _dump_ext_hash(ib=ib, ext_name=PRODUCT, filename=checksum_filename)
    ib.dump_cfe(cfe=f"build/{target}.cfe", ext_name=PRODUCT)
    
    # bundle
    bundle = pie.bundle.Bundle(PRODUCT, SYNONYM, version, SERVICE)
    bundle.append_extension(PRODUCT, version, f"build/{target}.cfe")
    bundle.variables["UPDSERVICE_LOCATION"] = UPDSERVICE_LOCATION
    bundle.build(f"build/{target}.{version}.epf")


# Тесты


def test_ui():

    ib = _base()
    ib.load_cfe(cfe="build/kedo_zup.cfe", ext_name="КЭДО")

    _install_stage(ib=ib, stage=_env('KEDO_STAGE'))
    #
    va = pie.testframework.TestFramework()
    va.va_path = os.path.abspath(os.getenv("RUNNER_PATHVANESSA"))
    
    filter = os.getenv("FILTER", "zup3")
    ignore = os.getenv("IGNORE", "")

    va.read_settings_from_file("./tools/json/VAParams.json")

    if filter:
        va.add_tags_filter(filter)
    if ignore:
        va.add_tags_ignore(ignore)

    va.run(ib=ib, timeout=2000)
    va.dump(junit="build/junit.xml")
    va.print()
    va.raise_for_status()
    time.sleep(60)


def test_unit():

    ib = _base()
    ib.load_cfe(cfe="build/kedo_zup.cfe", ext_name="КЭДО")
    ib.load_ext(ext_src="src/kedo_test", ext_name="КЭДОТестирование", update=True)
    _disable_ext_flags(ib=ib, ext_name="КЭДОТестирование")

    _install_stage(ib=ib, stage=_env('KEDO_STAGE'))

    test = pie.testframework.TestFramework(cov_measure=False)
    test.va_path = os.path.abspath(os.getenv("RUNNER_PATHVANESSA"))

    test.test_pattern = f"src/kedo_test/DataProcessors/КЭДОТ_ТестыЗУП.xml"
    test.va_settings.mdo_lib = [
        "Обработка.КЭДОТ_ТестыЗУП.Форма.Форма"
    ]

    test.run(ib=ib, timeout=600)
    test.dump(junit="build/reports/allurereport/junit.xml")
    test.print()
    test.raise_for_status()


def release():
    import kontur.updservice as upd

    product_name = "kedo_zup"

    version_info = versioning.load_version_info("build/kedo_zup_version_info.json")
    version = version_info.version
    release_date = datetime.date.today().strftime("%d.%m.%Y")
    checksum_filename = _checksum_filename(product_name)
    with open(checksum_filename, "r", encoding="utf-8-sig") as f:
        checksum = f.read()

    client = upd.Client(UPDSERVICE_LOCATION, api_key=API_KEY)
    
    # Загрузка контента
    contents = [
        (
            "build/kedo_zup.cfe", 
            f"kedo_zup.{version}.cfe", 
            upd.ContentTypes.Ext
        ),
        (
            f"build/kedo_zup.{version}.epf",
            f"kedo_zup.{version}.epf",
            upd.ContentTypes.Epf
        ),
    ]

    for filepath, filename, content_type in contents:
        client.post_content(
            product=product_name,
            version=version,
            file_obj=open(filepath, "rb"),
            file_name=filename,
            content_type=content_type,
        )
    
    # Дата релиза
    client.set_release_date_description(
        product_name=product_name,
        version=version,
        release_date=release_date,
        description=""
    )

    # Хеш-сумма
    client.put_content(
        product=product_name, 
        version=version, 
        content=upd.ContentTypes.Ext, 
        data=upd.model.PutContentRequest(src_checksum=checksum)
    )


# Служебные


def _ib_bp3():
    username = _env("IB_USERNAME_BP3")
    password = _env("IB_PASSWORD")
    name = _env("IB_BP3")
    auth = pie.ib.Auth(username=username, password=password)
    connector = pie.ib.ListConnector(auth=auth, name=name)
    ib = pie.ib.InfoBase(connector)
    return ib


def _ib(custom_path=None):
    username = _env("IB_USERNAME")
    password = _env("IB_PASSWORD")
    if custom_path is None:
        name = _env("IB")
    else:
        name = custom_path
    auth = pie.ib.Auth(username=username, password=password)
    connector = pie.ib.ListConnector(auth=auth, name=name)
    ib = pie.ib.InfoBase(connector)
    return ib


def _ib_zup(custom_path=None):
    username = _env("IB_USERNAME")
    password = _env("IB_PASSWORD")
    if custom_path is None:
        name = _env("IB_ZUP")
    else:
        name = custom_path
    auth = pie.ib.Auth(username=username, password=password)
    connector = pie.ib.ListConnector(auth=auth, name=name)
    ib = pie.ib.InfoBase(connector)
    return ib


def _ib_erp():
    username = pie.os.environ.get("IB_USERNAME_ERP")
    password = pie.os.environ.get("IB_PASSWORD")
    name = pie.os.environ.get("IB_ERP")
    auth = pie.ib.Auth(username=username, password=password)
    connector = pie.ib.ListConnector(auth=auth, name=name)
    ib = pie.ib.InfoBase(connector)
    return ib


def _ib_upp():
    username = _env("IB_USERNAME_UPP")
    password = _env("IB_PASSWORD")
    name = _env("IB_UPP")
    auth = pie.ib.Auth(username=username, password=password)
    connector = pie.ib.ListConnector(auth=auth, name=name)
    ib = pie.ib.InfoBase(connector)
    return ib


def _base():
    username = _env("BASE_USR")
    password = _env("BASE_PWD")
    file = _env("BASE_REF")
    auth = pie.ib.Auth(username=username, password=password)
    connector = pie.ib.FileConnector(auth=auth, file=file)
    ib = pie.ib.InfoBase(connector)
    return ib


def _disable_ext_flags(ib: pie.ib.InfoBase, ext_name: str):

    epf_path = f"build/{DISABLE_FLAGS_EPF}.epf"

    pie.build_epf(
        epf=epf_path,
        epf_xml=f"tools/src/{DISABLE_FLAGS_EPF}/{DISABLE_FLAGS_EPF}.xml",
        ib=ib
    )

    ib.exec(epf=epf_path, args=f"ИмяРасширения={ext_name}")

def _install_stage(ib: pie.ib.InfoBase, stage: str):

    epf_path = f"build/{INSTALL_STAGE_EPF}.epf"

    pie.build_epf(
        epf=epf_path,
        epf_xml=f"tools/src/{INSTALL_STAGE_EPF}/{INSTALL_STAGE_EPF}.xml",
        ib=ib
    )

    ib.exec(epf=epf_path, args=f"stage={stage}")

def _dump_ext_hash(ib: pie.ib.InfoBase, ext_name: str, filename: str) -> str:

    epf_path = f"build/{SAVE_HASH_EPF}.epf"
    
    pie.build_epf(
        epf=epf_path,
        epf_xml=f"tools/src/{SAVE_HASH_EPF}/{SAVE_HASH_EPF}.xml",
        ib=ib
    )

    ib.exec(epf_path, f"ИмяРасширения={ext_name};ИмяФайла={filename}")


def _checksum_filename(product_name: str) -> str:
    return f"build/{product_name}_checksum.txt"


def install_va():
    command = ["opm", "install", "-l", f"vanessa-automation@1.2.041.1"]
    subprocess.call(command)


def fix_dupl(src = 'src/kedo_zup'):

    result = duplicate_ids.check_all_form_xml_in_src(src)

    for file_path, duplicates_by_category in result:
        for category, values in duplicates_by_category.items():
            maxid = values['МаксимальныйID']
            duplicates = values['Дубликаты']
            if duplicates:
                for elem_id, occurrences in duplicates.items():
                    for occ in occurrences:
                        name = occ['attributes'].get('name', 'Без имени')
                        str1 = f'name="{name}" id="{elem_id}"'
                        str2 = f'name="{name}" id="{maxid + 1}"'
                        replace_line_in_file(file_path, str1, str2)
                        maxid = maxid + 1
                        break


    return 

def replace_line_in_file(file_path, old_line, new_line):
    # Читаем содержимое файла
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Заменяем старую строку на новую
    updated_content = content.replace(old_line, new_line)

    # Перезаписываем файл, если были изменения
    if updated_content != content:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(updated_content)