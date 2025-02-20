# PUB Acelerômetro - Servidor Bluetooth

## Como rodar o código

1. Criar um ambiente virtual para o projeto
   É uma boa prática criar um ambiente virtual para separar as dependências do projeto da sua máquina. Para isso, abra um terminal na pasta do repositório e entre:

```
python -m venv . 
source ./bin/activate
```

2. Em seguida, devido à biblioteca PyBluez, precisamos instalar algumas bibliotecas de desenvolvimento, como `libbluetooth-dev` e `build-essential`. Dependendo de seu sistema operacional, o nome desses pacotes será diferente.
3. Após instalar as bibliotecas acima, e, dentro do ambiente virtual, podemos baixar as dependências do projeto:

`pip install -r requirements.txt`

4. Entre no arquivo `app_config.py` e defina o caminho para `SERVER_LOG_FILE_PATH`. Por padrão, o caminho é `server.log`.

5. Por fim, para iniciar o servidor, execute a `main.py` no seu terminal:

`python main.py`
