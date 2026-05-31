"""Módulo de exemplo com operações matemáticas e utilitárias."""

from math import sqrt  # função importada: NÃO deve virar comando


def ola(nome: str, saudacao="Olá"):
    """Exibe uma saudação personalizada.

    Args:
        nome: Nome da pessoa a ser saudada.
        saudacao: Palavra de saudação (padrão: 'Olá').
    """
    print(f"{saudacao}, {nome}!")


def soma(a: int, b: int = 0) -> int:
    """Retorna a soma de dois números inteiros.

    Args:
        a: Primeiro número
        b: Segundo número (padrão = 0)

    Returns:
        Soma calculada
    """
    resultado = a + b
    print(resultado)
    return resultado


def ativo(debug: bool = False):
    """Controla o modo de depuração do sistema."""
    print("Debug ativado" if debug else "Modo normal")


def multiplica(a: int, b: int) -> int:
    """Multiplica a por b. Parâmetros: a (int), b (int)."""
    resultado = a * b
    print(resultado)
    return resultado


def _interna():
    """Função auxiliar privada (continua sendo global, vira comando)."""

    def aninhada():  # função interna: NÃO deve virar comando
        return 42

    return aninhada()
