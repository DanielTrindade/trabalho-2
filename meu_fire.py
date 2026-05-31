#!/usr/bin/env python3
"""Implementação de mini-Fire.

Transforma qualquer arquivo Python em uma interface de linha de comando (CLI)
usando meta-programação: carrega o módulo dinamicamente, inspeciona as funções
definidas em seu nível global e gera, automaticamente, um subcomando para cada
uma — com parsing de argumentos e ajuda extraída das docstrings.

Uso:
    python meu_fire.py <arquivo.py> [comando] [args...]
    python meu_fire.py <arquivo.py> --help
    python meu_fire.py <arquivo.py> <comando> --help
"""

import sys
import os
import re
import inspect
import importlib.util
from typing import Any, Callable

# Palavras aceitas para conversão de booleanos (requisito do enunciado).
BOOL_TRUE = {"true", "yes", "1"}
BOOL_FALSE = {"false", "no", "0"}


# --------------------------------------------------------------------------- #
# Carregamento dinâmico do módulo e descoberta de funções
# --------------------------------------------------------------------------- #
def carregar_modulo(caminho: str):
    """Carrega dinamicamente um módulo Python a partir do caminho de um arquivo."""
    nome = os.path.splitext(os.path.basename(caminho))[0]
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def descobrir_funcoes(modulo) -> list[tuple[str, Callable]]:
    """Retorna as funções definidas no nível global do módulo, em ordem de definição.

    Exclui funções importadas de outros módulos (``__module__`` diferente).
    Métodos, classes e funções aninhadas não aparecem em ``getmembers`` neste
    nível, portanto já ficam de fora.
    """
    funcoes = [
        (nome, obj)
        for nome, obj in inspect.getmembers(modulo, inspect.isfunction)
        if obj.__module__ == modulo.__name__
    ]
    # Ordena por linha de definição para preservar a ordem do arquivo
    # (getmembers devolve em ordem alfabética).
    funcoes.sort(key=lambda par: par[1].__code__.co_firstlineno)
    return funcoes


# --------------------------------------------------------------------------- #
# Introspecção de tipos e docstrings
# --------------------------------------------------------------------------- #
def nome_tipo(param: inspect.Parameter) -> str:
    """Nome amigável do tipo de um parâmetro (a partir da anotação ou do padrão)."""
    anotacao = param.annotation
    if anotacao is not inspect.Parameter.empty and hasattr(anotacao, "__name__"):
        return anotacao.__name__
    if param.default not in (inspect.Parameter.empty, None):
        return type(param.default).__name__
    return "str"


def eh_booleano(param: inspect.Parameter) -> bool:
    """Diz se o parâmetro deve ser tratado como flag booleana."""
    return param.annotation is bool or isinstance(param.default, bool)


def parsear_docstring(doc: str | None) -> tuple[str, dict[str, str], str]:
    """Extrai (resumo, descrições dos parâmetros, texto de retorno) de uma docstring.

    Aceita o formato Mínimo (apenas a primeira linha é usada como resumo) e o
    formato Google (seções ``Args:`` e ``Returns:``).
    """
    if not doc:
        return "", {}, ""

    linhas = doc.split("\n")
    resumo = next((ln.strip() for ln in linhas if ln.strip()), "")

    args: dict[str, str] = {}
    retorno = ""
    secao: str | None = None
    for ln in linhas:
        chave = ln.strip().lower().rstrip(":")
        if chave in ("args", "arguments", "parâmetros", "parametros"):
            secao = "args"
            continue
        if chave in ("returns", "return", "retorna"):
            secao = "returns"
            continue
        texto = ln.strip()
        if secao == "args":
            # Formato "nome: descrição" ou "nome (tipo): descrição".
            m = re.match(r"(\w+)\s*(?:\([^)]*\))?\s*:\s*(.*)", texto)
            if m:
                args[m.group(1)] = m.group(2).strip()
        elif secao == "returns" and texto:
            retorno = (retorno + " " + texto).strip()
    return resumo, args, retorno


# --------------------------------------------------------------------------- #
# Geração de ajuda
# --------------------------------------------------------------------------- #
def descrever_parametro(nome: str, param: inspect.Parameter, descricoes: dict[str, str]) -> str:
    """Linha descritiva de um parâmetro para a ajuda (ex.: ``--a (int, obrigatório): ...``)."""
    tipo = nome_tipo(param)
    if param.default is inspect.Parameter.empty:
        situacao = "obrigatório"
    else:
        situacao = f"padrão={param.default!r}"
    linha = f"--{nome} ({tipo}, {situacao})"
    desc = descricoes.get(nome)
    if desc:
        linha += f": {desc}"
    return linha


def ajuda_geral(modulo, caminho: str, funcoes: list[tuple[str, Callable]]) -> None:
    """Imprime a ajuda geral: docstring do módulo e lista de comandos."""
    resumo_modulo, _, _ = parsear_docstring(modulo.__doc__)
    print(f"\nMódulo: {os.path.basename(caminho)}")
    if resumo_modulo:
        print(f"Descrição: {resumo_modulo}")
    print("\nComandos disponíveis:")

    largura = max((len(nome) for nome, _ in funcoes), default=0) + 2
    for nome, func in funcoes:
        resumo, args, _ = parsear_docstring(inspect.getdoc(func))
        print(f"  {nome:<{largura}}- {resumo}")
        sig = inspect.signature(func)
        if sig.parameters:
            print("  Parâmetros:")
            for nome_p, param in sig.parameters.items():
                print(f"      {descrever_parametro(nome_p, param, args)}")
        print()


def ajuda_comando(nome: str, func: Callable) -> None:
    """Imprime a ajuda específica de um comando."""
    resumo, args, retorno = parsear_docstring(inspect.getdoc(func))
    sig = inspect.signature(func)

    print(f"\nComando: {nome}")
    if resumo:
        print(f"Descrição: {resumo}")

    partes_uso = []
    for nome_p, param in sig.parameters.items():
        if eh_booleano(param):
            token = f"--{nome_p}"
        else:
            token = f"--{nome_p} {nome_tipo(param).upper()}"
        if param.default is inspect.Parameter.empty:
            partes_uso.append(token)
        else:
            partes_uso.append(f"[{token}]")
    print(f"\nUso: {nome} {' '.join(partes_uso)}".rstrip())

    if sig.parameters:
        print("\nParâmetros:")
        for nome_p, param in sig.parameters.items():
            print(f"  {descrever_parametro(nome_p, param, args)}")

    if retorno:
        print(f"\nRetorna: {retorno}")


# --------------------------------------------------------------------------- #
# Conversão de valores e execução
# --------------------------------------------------------------------------- #
def converter(valor: str, param: inspect.Parameter, nome: str) -> Any:
    """Converte uma string da linha de comando para o tipo esperado do parâmetro."""
    tipo = nome_tipo(param)
    try:
        if eh_booleano(param):
            baixo = valor.lower()
            if baixo in BOOL_TRUE:
                return True
            if baixo in BOOL_FALSE:
                return False
            raise ValueError
        if tipo == "int":
            return int(valor)
        if tipo == "float":
            return float(valor)
        return valor  # str (ou tipo sem anotação)
    except (ValueError, TypeError):
        raise ValueError(f"Erro: Parâmetro '{nome}' esperava {tipo}, recebeu '{valor}'")


def parsear_e_executar(nome: str, func: Callable, argumentos: list[str]) -> None:
    """Faz o parsing dos argumentos da CLI conforme a assinatura e executa a função."""
    sig = inspect.signature(func)
    parametros = sig.parameters
    fornecidos: dict[str, Any] = {}
    posicionais: list[str] = []

    i = 0
    while i < len(argumentos):
        token = argumentos[i]
        if token.startswith("--"):
            nome_p = token[2:]
            param = parametros.get(nome_p)
            if param is None:
                print(f"Erro: Parâmetro '--{nome_p}' não existe no comando '{nome}'.")
                return
            if eh_booleano(param):
                # --flag pode vir sozinha ou seguida de um valor booleano explícito.
                proximo = argumentos[i + 1] if i + 1 < len(argumentos) else None
                if proximo is not None and not proximo.startswith("--") \
                        and proximo.lower() in (BOOL_TRUE | BOOL_FALSE):
                    fornecidos[nome_p] = converter(proximo, param, nome_p)
                    i += 2
                else:
                    # Presença da flag = oposto do valor padrão.
                    fornecidos[nome_p] = not bool(param.default)
                    i += 1
            else:
                if i + 1 >= len(argumentos):
                    print(f"Erro: Parâmetro '--{nome_p}' espera um valor.")
                    return
                fornecidos[nome_p] = converter(argumentos[i + 1], param, nome_p)
                i += 2
        else:
            posicionais.append(token)
            i += 1

    # Preenche os parâmetros obrigatórios (sem padrão) ainda não dados por nome.
    obrigatorios = [
        n for n, p in parametros.items()
        if p.default is inspect.Parameter.empty and n not in fornecidos
    ]
    if len(posicionais) < len(obrigatorios):
        total = sum(1 for p in parametros.values() if p.default is inspect.Parameter.empty)
        print(f"Erro: Função '{nome}' requer {total} argumentos posicionais")
        return
    for nome_p, valor in zip(obrigatorios, posicionais):
        fornecidos[nome_p] = converter(valor, parametros[nome_p], nome_p)

    func(**fornecidos)


# --------------------------------------------------------------------------- #
# Função principal
# --------------------------------------------------------------------------- #
def meu_fire(caminho_modulo: str) -> None:
    """Gera e executa uma CLI a partir do arquivo Python informado.

    Lê ``sys.argv[2:]`` para descobrir o comando e seus argumentos.
    """
    if not os.path.isfile(caminho_modulo):
        print(f"Erro: Arquivo '{caminho_modulo}' não encontrado")
        return

    try:
        modulo = carregar_modulo(caminho_modulo)
    except Exception as exc:  # erro ao importar o módulo do usuário
        print(f"Erro: Falha ao carregar '{caminho_modulo}': {exc}")
        return

    funcoes = descobrir_funcoes(modulo)
    mapa = dict(funcoes)

    argv = sys.argv[2:]
    comando = argv[0] if argv else None

    # Ajuda geral: sem comando ou pedido explícito de ajuda.
    if comando is None or comando in ("--help", "-h", "help", "ajuda"):
        ajuda_geral(modulo, caminho_modulo, funcoes)
        return

    if comando not in mapa:
        print(f"Erro: Comando '{comando}' não encontrado. Use --help para listar.")
        return

    resto = argv[1:]
    if resto and resto[0] in ("--help", "-h", "help", "ajuda"):
        ajuda_comando(comando, mapa[comando])
        return

    try:
        parsear_e_executar(comando, mapa[comando], resto)
    except ValueError as erro:  # erros de conversão de tipo já formatados
        print(str(erro))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python meu_fire.py <arquivo.py> [comando] [args...]")
        sys.exit(1)

    caminho = sys.argv[1]
    meu_fire(caminho)
