# LP 2026-1 — Lista de Exercícios II

Universidade Federal do Amazonas — Instituto de Computação
Linguagens de Programação (Prof. Dr. Marco Cristo)

Programação OO, Meta-programação, Agentes e LLMs.

## Estrutura

| Arquivo | Parte | Descrição |
|---------|-------|-----------|
| `lista2_SEMrespostas.ipynb` | I, II e III | Notebook principal da lista (deliverable). |
| `Matriz2D.kt` | I (1.1) | Classe imutável `Matriz2D` em Kotlin, com operadores sobrecarregados. |
| `meu_fire.py` | II | Mini-Fire: gera uma CLI a partir de um arquivo Python via meta-programação. |
| `exemplo.py` | II | Módulo de exemplo para testar o `meu_fire.py`. |
| `nota-secreta-a2a-alunos.zip` | III | Material fornecido pelo professor (agentes A2A / LLM). |
| `lista2.pdf` | — | Enunciado da lista. |

## Como executar

### Parte I — Matriz2D (Kotlin)

```bash
kotlinc Matriz2D.kt -include-runtime -d Matriz2D.jar
java -jar Matriz2D.jar
```

### Parte II — meu_fire (Python)

```bash
python meu_fire.py exemplo.py --help            # ajuda geral
python meu_fire.py exemplo.py soma 10 --b 20     # 30
python meu_fire.py exemplo.py ola --nome Ana     # Olá, Ana!
python meu_fire.py exemplo.py soma --help        # ajuda do comando
```

## Integrantes

- _A preencher_
