# PUB Acelerômetro - Servidor Bluetooth

Para visualizar os .gifs, extraia [este arquivo](https://drive.google.com/file/d/17iuaz6CuGuShrBwceKWjnoN6XGb0ZeZD/view?usp=sharing) aqui.

## Instalando os pacotes necessários no seu sistema operacional Linux

1. Vamos instalar todas as bibliotecas necessárias para rodar o servidor, considerando que é seu primeiro contato com um sistema operacional Linux. Considerando que você está usando um sistema operacional cujo administrador de pacotes é o Aptitude, como Ubuntu, Linux Mint e Debian, abra seu terminal e digite:

`sudo apt update` // Para buscar as versões mais atualizadas  
`sudo apt install git python3 libbluetooth-dev build-essential python3.12-venv python3-dev` // Para instalar os pacotes necessários

![Instalar pacotes do SO](install_packages.gif)

2. Em seguida, vamos acessar o site do [VSCode](https://code.visualstudio.com) para instalar o editor de texto. Clique no botão ".deb", para instalar o pacote.

3. Em seguida, considerando que você está na sua pasta "home", abra o terminal novamente e digite:

`cd Downloads/` // cd significa "change directory"

4. Por fim, vamos instalar o novo pacote:

`sudo apt install ./code_1.99.3-1744761595_amd64.deb` // o nome do arquivo pode mudar conforme a versão

![Instalar o VSCode](install_vscode.gif)

5. Ao finalizar a instalação, podemos baixar este projeto na nossa máquina. Acesse [o link do repositório](https://github.com/feliplpz/PUB_Servidor), e clique em Code, depois, copie o link em HTTPS.

6. Acesse o terminal novamente, digite `cd  ~` para voltar à "home". Em seguida, vamos clonar o repositório na máquina digitando `git clone https://github.com/feliplpz/PUB_Servidor.git`, colando o link HTTPS que copiamos no passo 5.

7. Agora, podemos abrir o código usando nosso editor de texto, através do comando `code PUB_Servidor`.

![Clonar repositório e abrir o VSCode](clone_repo_open_code.gif)

## Como rodar o código

1. Criar um ambiente virtual para o projeto  

É uma boa prática criar um ambiente virtual para separar as dependências do projeto da sua máquina. Para isso, abra um terminal na pasta do repositório e entre:

```
python3 -m venv .venv 
source .venv/bin/activate
```

2. Após instalar as bibliotecas acima, e, dentro do ambiente virtual, podemos baixar as dependências do projeto:

`pip install -r requirements.txt`

![Gerar venv e instalar requerimentos](venv_install_reqs.gif)

4. Entre no arquivo `.env` e defina o caminho para `SERVER_LOG_FILE_PATH`. Por padrão, o caminho é `server.log`.

5. É possível definir, também, uma pasta para armazenar todas as experiências, no arquivo `.env`. Entre o caminho da pasta desejada na variável `DATA_FILE_PATH`. Por padrão, está utilizando a própria pasta do servidor. Importante: certifique-se que a pasta exista no caminho que você declarou.

6. Por fim, para iniciar o servidor, execute a `app.py` no seu terminal:

`python3 app.py`

![Rodar o servidor](run_server.gif)
