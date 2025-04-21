import io
import os
import datetime
import platform
import re
import subprocess
import time
import zipfile
from decimal import Decimal
from typing import List, Tuple

import requests
import typer
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()

app = typer.Typer()


class ItemNotaFiscal(BaseModel):
    descricao: str
    quantidade: Decimal
    valor_unitario: Decimal


class TomadorNotaFiscal(BaseModel):
    razao_social: str
    endereco: str
    numero: str
    complemento: str
    uf: str
    municipio: str


class NotaFiscal(BaseModel):
    tomador: TomadorNotaFiscal
    data: datetime.date
    natureza_operacao: str
    item_lista_servicos: str
    cnae: str
    items: List[ItemNotaFiscal]
    iss_retido: bool
    outras_informacoes: str


def get_latest_chromedriver(chrome_version):
    """Downloads the latest compatible ChromeDriver using Chrome for Testing."""

    dashboard_url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
    response = requests.get(dashboard_url)
    response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
    data = response.json()

    version_data = data["channels"]["Stable"]["downloads"]["chromedriver"]

    # find the correct download url.
    download_url = None

    if platform.system() == "Darwin" and platform.machine() == "arm64":
        platform_key = "mac-arm64"
    elif platform.system() == "Darwin" and platform.machine() == "x86_64":
        platform_key = "mac-x64"
    elif platform.system() == "Linux":
        platform_key = "linux64"
    elif platform.system() == "Windows":
        platform_key = "win64"
    else:
        raise Exception("Unsupported OS")

    for entry in version_data:
        if entry["platform"] == platform_key:
            download_url = entry["url"]
            break

    if download_url is None:
        raise Exception(f"ChromeDriver not found for platform {platform_key}")

    response = requests.get(download_url)
    response.raise_for_status()
    zip_file = zipfile.ZipFile(io.BytesIO(response.content))
    chromedriver_name = (
        "chromedriver-"
        + platform_key
        + "/chromedriver"
        + (".exe" if platform.system() == "Windows" else "")
    )
    zip_file.extract(chromedriver_name, ".")
    os.chmod(chromedriver_name, 0o755)  # Make executable
    return os.path.abspath(chromedriver_name)


def get_chrome_version():
    """Gets the Chrome browser version."""
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    "--version",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip().split(" ")[2].split(".")[0]
        except FileNotFoundError:
            return None
    elif platform.system() == "Linux":
        try:
            result = subprocess.run(
                ["google-chrome", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip().split(" ")[2].split(".")[0]
        except FileNotFoundError:
            return None
    elif platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["chrome", "--version"], capture_output=True, text=True, check=True
            )
            return result.stdout.strip().split(" ")[2].split(".")[0]
        except FileNotFoundError:
            return None
    return None


def activate_iframe(driver, locator: Tuple[str, str], timeout: int = 10):
    """Activates the iframe specified by the locator."""
    try:
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(locator)
        )
        driver.switch_to.frame(iframe)
        return iframe
    except Exception as e:
        print(f"Error activating iframe: {e}")
        raise


def click_button(driver, locator: Tuple[str, str], timeout: int = 10):
    """Clicks a button specified by the locator."""
    try:
        button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(locator)
        )
        button.click()
        return button
    except Exception as e:
        print(f"Error clicking button: {e}")
        raise


def select_option(driver, tab: str, label: str, option_text: str, timeout: int = 10):
    """Selects an option from a dropdown specified by the tab, label, and option text."""
    try:
        select_input = driver.find_element(
            By.XPATH, f"//div[@id='{tab}']//label[contains(text(), '{label}')]"
        ).get_attribute("for")
        click_button(
            driver,
            (
                By.XPATH,
                f"//div[@id='{tab}']//input[@id='{select_input}']/following-sibling::button",
            ),
        )
        component_id = re.match(r"[^0-9]+([0-9]+)", select_input).group(1)
        click_button(
            driver,
            (
                By.XPATH,
                f"//div[@id='lookupDetails{component_id}']//li[contains(text(), '{option_text}')]",
            ),
        )
    except Exception as e:
        print(f"Error selecting option {option_text} for {label}: {e}")
        raise


def select_radio(driver, tab: str, label: str, option_text: str, timeout: int = 10):
    """Selects a radio button specified by the tab, label, and option text."""
    try:
        radio_input = driver.find_element(
            By.XPATH, f"//div[@id='{tab}']//label[contains(text(), '{label}')]"
        ).get_attribute("id")
        component_id = re.match(r"[^0-9]+([0-9]+)", radio_input).group(1)
        radio_id = driver.find_element(
            By.XPATH,
            f"//input[@name='WFRInput{component_id}']/following-sibling::div//label[contains(text(), '{option_text}')]",
        ).get_attribute("for")
        click_button(driver, (By.XPATH, f"//input[@id='{radio_id}']"))
    except Exception as e:
        print(f"Error selecting radio option {option_text} for {label}: {e}")
        raise


def send_keys(driver, tab: str, label: str, keys: str, timeout: int = 10):
    """Sends keys to an input field specified by the locator."""
    try:
        label_for = (
            WebDriverWait(driver, timeout)
            .until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        f"//div[@id='{tab}']//label[contains(text(), '{label}')]",
                    )
                )
            )
            .get_attribute("for")
        )
        input_field = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, label_for))
        )
        input_field.clear()
        input_field.send_keys(keys)
    except Exception as e:
        print(f"Error sending keys to input field: {e}")
        raise


def automate_natal_nfe(cnpj, password, nota_fiscal: NotaFiscal, chromedriver_path: str):
    """Automates the Natal NFS-e emission process."""
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service)

    try:
        driver.get("https://directa.natal.rn.gov.br/")

        driver.find_element(By.NAME, "user").send_keys(cnpj)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.XPATH, '//input[@value="Entrar"]').click()

        activate_iframe(driver, (By.NAME, "mainsystem"))
        activate_iframe(driver, (By.NAME, "mainform"))

        elemento = click_button(
            driver, (By.XPATH, "//a[.//span[text()='Nota Natalense']]")
        )

        submenu = elemento.get_attribute("href").split("#")[-1]
        print(f"Abrindo o submenu de Nota Natalense: {submenu}")

        elemento = click_button(
            driver,
            (By.XPATH, f"//div[@id='{submenu}']//a[.//span[text()='Operações']]"),
        )

        submenu = elemento.get_attribute("href").split("#")[-1]
        print(f"Abrindo o submenu de Operações: {submenu}")

        click_button(
            driver,
            (By.XPATH, f"//div[@id='{submenu}']//a[.//span[text()='Emitir NFS-e']]"),
        )
        activate_iframe(driver, (By.XPATH, "//*[@id='AbaContainer']//iframe"))
        activate_iframe(driver, (By.NAME, "mainform"))
        click_button(
            driver, (By.XPATH, "//div[@id='tab1']//button[.//span[text()='Próximo']]")
        )
        click_button(
            driver,
            (
                By.XPATH,
                "//div[@id='tab2']//label[contains(text(), 'Não informar')]/preceding-sibling::input",
            ),
        )
        driver.find_element(
            By.XPATH, "//div[@id='tab2']//div[@id='txtRazaoSocialTomador']//input"
        ).send_keys(nota_fiscal.tomador.razao_social)
        driver.find_element(
            By.XPATH, "//div[@id='tab2']//div[@id='txtEnderecoTomador']//input"
        ).send_keys(nota_fiscal.tomador.endereco)
        driver.find_element(
            By.XPATH, "//div[@id='tab2']//div[@id='txtNumeroTomador']//input"
        ).send_keys(nota_fiscal.tomador.numero)
        driver.find_element(
            By.XPATH, "//div[@id='tab2']//div[@id='txtComplementoTomador']//input"
        ).send_keys(nota_fiscal.tomador.complemento)
        select_option(driver, "tab2", "UF", nota_fiscal.tomador.uf)
        select_option(driver, "tab2", "Município", nota_fiscal.tomador.municipio)

        click_button(
            driver, (By.XPATH, "//div[@id='tab2']//button[.//span[text()='Próximo']]")
        )

        date_picker_input_id = (
            WebDriverWait(driver, 10)
            .until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//div[@id='tab3']//label[contains(text(), 'Data da Prestação do Serviço')]",
                    )
                )
            )
            .get_attribute("for")
        )
        date_picker = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, date_picker_input_id))
        )
        date_picker.clear()
        date_picker.send_keys(nota_fiscal.data.strftime("%d/%m/%Y"))
        select_option(
            driver, "tab3", "Natureza da Operação", nota_fiscal.natureza_operacao
        )
        select_option(
            driver, "tab3", "Item da Lista de Serviços", nota_fiscal.item_lista_servicos
        )
        select_option(driver, "tab3", "CNAE - Código de Atividade", nota_fiscal.cnae)

        click_button(
            driver, (By.XPATH, "//div[@id='tab3']//button[.//span[text()='Próximo']]")
        )

        for item in nota_fiscal.items:
            send_keys(driver, "tab4", "Discriminação do Serviço", item.descricao)
            send_keys(
                driver, "tab4", "Quantidade", str(item.quantidade).replace(".", ",")
            )
            send_keys(
                driver,
                "tab4",
                "Preço Unitário",
                str(item.valor_unitario.quantize(Decimal("0.01"))).replace(".", ","),
            )

            click_button(
                driver,
                (By.XPATH, "//div[@id='tab4']//button[.//span[text()='Incluir']]"),
            )
            time.sleep(1)

        select_radio(
            driver,
            "tab4",
            "ISS Retido pelo Tomador?",
            "Sim" if nota_fiscal.iss_retido else "Não",
        )
        click_button(
            driver, (By.XPATH, "//div[@id='tab4']//button[.//span[text()='Próximo']]")
        )

        send_keys(driver, "tab5", "Outras Informações", nota_fiscal.outras_informacoes)
        click_button(
            driver, (By.XPATH, "//div[@id='tab5']//button[.//span[text()='Próximo']]")
        )

        confirmation = None
        while confirmation not in {"y", "n"}:
            confirmation = (
                input(
                    "Verifique o resumo da NFS-e no Google Chrome. Confirma a emissão da NFS-e? (y/n): "
                )
                .strip()
                .lower()
            )
        if confirmation == "n":
            print("Emissão cancelada.")
            return

        breakpoint()

        click_button(
            driver,
            (By.XPATH, "//div[@id='tab6']//button[.//span[text()='Gerar NFS-e']]"),
        )

        breakpoint()

        time.sleep(10)

        confirmation = None
        while confirmation not in {"ok", "y"}:
            confirmation = input("NFS-e emitida. Favor verificar. [ok]").strip().lower()

    finally:
        driver.quit()


def parse_yaml_to_notafiscal(filename: str) -> NotaFiscal:
    """
    Parses a YAML file into a NotaFiscal Pydantic object.

    Args:
        filename: The path to the YAML file.

    Returns:
        A NotaFiscal object populated with data from the YAML file.
    """
    try:
        with open(filename, "r") as f:
            yaml_data = yaml.safe_load(f)
        return NotaFiscal(**yaml_data)
    except FileNotFoundError:
        typer.echo(f"Error: File not found at '{filename}'", err=True)
        raise typer.Exit(code=1)
    except yaml.YAMLError as e:
        typer.echo(f"Error parsing YAML in '{filename}': {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"An unexpected error occurred: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def gerar_nota(
    filename: str = typer.Argument(
        ..., help="Path to the YAML file containing NotaFiscal data."
    ),
):
    """
    Parses a YAML file and displays the Nota Fiscal information.
    """

    nota_fiscal = parse_yaml_to_notafiscal(filename)

    cnpj = os.environ.get("NOTA_FISCAL_CNPJ")
    password = os.environ.get("NOTA_FISCAL_PASSWORD")

    if not cnpj or not password:
        print(
            "Error: CNPJ and password must be set as environment variables (NOTA_FISCAL_CNPJ, NOTA_FISCAL_PASSWORD)."
        )
        return

    chrome_version = get_chrome_version()
    if not chrome_version:
        print("Error: Chrome not found.")
        return

    chromedriver_path = get_latest_chromedriver(chrome_version)
    if not chromedriver_path:
        return

    automate_natal_nfe(cnpj, password, nota_fiscal, chromedriver_path)
    os.remove(chromedriver_path)  # remove the chromedriver after usage.


if __name__ == "__main__":
    app()
