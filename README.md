# Script para criação de nota fiscal na prefeitura de Natal/RN

Este projeto facilita a emissão de nota fiscal em Natal/RN. Esta não é uma ferramenta oficial, apenas um projeto pessoal para facilitar o meu dia a dia. Use sob sua própria conta e risco.

O script é construído usando Selenium para interagir com o navegador Google Chrome.
Ele executa os passos necessários no [Portal Directa](https://directa.natal.rn.gov.br/) para 
emissão de uma NFS-e seguindo a configuração fornecida em um aquivo YAML.

O script pode estar enviesado para o tipo de nota fiscal que eu preciso emitir. Se ele não 
atender a sua necessidade, peço que abra uma Issue relatando a necessidade ou um Pull Request
com as alterações necessárias.

## Como usar?

Este script foi testado em uma máquina rodando Python 13 no MacOS X 15.

### Pré-requisitos

- Python
- Google Chrome

Recomendo utilizar asdf para gestão de versões do python. Esse repositório já fornece o `.tool-versions` correto.

Também é disponibilizado o `.direnv`. Mais informações em: https://direnv.net/

### Instalação

Crie um ambiente virtual:

```sh
python -m venv .venv
```

Ative o ambiente virtual:

```sh
direnv allow . # Se estiver utilizando direnv
source .venv/bin/activate # Caso contrário
```

Instale as dependências:

```sh
pip install -r requirements.txt
```

### Executando o script

Faça uma cópia do arquivo de configurações do ambiente:

```sh
cp .env-sample .env
```

E altere os valores das variáveis `NOTA_FISCAL_CNPJ` e `NOTA_FISCAL_PASSWORD` para o seu CNPJ e
senha respectivamente.

Certifique-se de que você criou um arquivo de entrada para o script seguindo o formato do arquivo
[examples/nota_fiscal.yml](examples.nota_fiscal.yml). Recomenda-se que você adicione o seu arquivo
na pasta [input](input).

Em seguida, execute o script:

```sh
python gerar_nota input/<nome-do-arquivo>.yml
```

O script irá abrir uma janela do navegador Google Chrome e interagir com o Portal Directa preenchendo
os campos informados. Ao final, antes de proceder com a geração da nota fiscal, o script vai pedir
que você revise os dados da nota fiscal antes de proceder com a emissão.

```sh
Verifique o resumo da NFS-e no Google Chrome. Confirma a emissão da NFS-e? (y/n):
```

Se você selecionar `y`, a nota será emitida e o script encerrado.

!TODO
Adicionei um breakpoint ao fim da emissão da nota fiscal para que eu possa implementar a parte de download do arquivo PDF gerado.


