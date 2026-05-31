/**
 * Parte I - 1.1: classe imutável Matriz2D (m x n de inteiros).
 *
 * Compilar e executar fora do Jupyter:
 *   kotlinc Matriz2D.kt -include-runtime -d Matriz2D.jar
 *   java -jar Matriz2D.jar
 */

class Matriz2D(dados: List<List<Int>>) {
    // Cópia defensiva: garante imutabilidade mesmo que a lista original mude depois.
    private val dados: List<List<Int>> = dados.map { it.toList() }

    // A validação vem ANTES das propriedades 'linhas'/'colunas' para que uma
    // matriz vazia lance IllegalArgumentException (via require) e não
    // NoSuchElementException ao chamar first().
    init {
        require(this.dados.isNotEmpty()) { "Matriz não pode ser vazia" }
        val largura = this.dados.first().size
        require(largura > 0) { "Matriz não pode ter linhas vazias" }
        require(this.dados.all { it.size == largura }) {
            "Todas as linhas devem ter o mesmo tamanho"
        }
    }

    val linhas: Int = this.dados.size
    val colunas: Int = this.dados.first().size

    // ----------------------------------------------------------------------- //
    // Operadores sobrecarregados
    // ----------------------------------------------------------------------- //

    /** Soma elemento a elemento. */
    operator fun plus(outra: Matriz2D): Matriz2D {
        require(linhas == outra.linhas && colunas == outra.colunas) {
            "Dimensões incompatíveis para soma: ${linhas}x$colunas e ${outra.linhas}x${outra.colunas}"
        }
        return Matriz2D(dados.mapIndexed { i, linha ->
            linha.mapIndexed { j, valor -> valor + outra.dados[i][j] }
        })
    }

    /** Subtração elemento a elemento. */
    operator fun minus(outra: Matriz2D): Matriz2D {
        require(linhas == outra.linhas && colunas == outra.colunas) {
            "Dimensões incompatíveis para subtração: ${linhas}x$colunas e ${outra.linhas}x${outra.colunas}"
        }
        return Matriz2D(dados.mapIndexed { i, linha ->
            linha.mapIndexed { j, valor -> valor - outra.dados[i][j] }
        })
    }

    /** Multiplicação por constante (à direita): a * 2. */
    operator fun times(escalar: Int): Matriz2D =
        Matriz2D(dados.map { linha -> linha.map { it * escalar } })

    /** Produto matricial: a * b. */
    operator fun times(outra: Matriz2D): Matriz2D {
        require(colunas == outra.linhas) {
            "Multiplicação matricial inválida: ${linhas}x$colunas por ${outra.linhas}x${outra.colunas}"
        }
        return Matriz2D(
            (0 until linhas).map { i ->
                (0 until outra.colunas).map { j ->
                    (0 until colunas).sumOf { k -> dados[i][k] * outra.dados[k][j] }
                }
            }
        )
    }

    // ----------------------------------------------------------------------- //
    // Métodos
    // ----------------------------------------------------------------------- //

    /** Acesso a elemento: a[i, j]. */
    operator fun get(i: Int, j: Int): Int {
        if (i !in 0 until linhas || j !in 0 until colunas) {
            throw IndexOutOfBoundsException(
                "Índice ($i, $j) fora dos limites de uma matriz ${linhas}x$colunas"
            )
        }
        return dados[i][j]
    }

    /** Retorna uma nova matriz com linhas e colunas trocadas. */
    fun transpor(): Matriz2D =
        Matriz2D((0 until colunas).map { j ->
            (0 until linhas).map { i -> dados[i][j] }
        })

    /** Determinante (definido apenas para matrizes 2x2). */
    fun det(): Int {
        require(linhas == 2 && colunas == 2) {
            "Determinante definido apenas para matriz 2x2 (esta é ${linhas}x$colunas)"
        }
        return dados[0][0] * dados[1][1] - dados[0][1] * dados[1][0]
    }

    /** Ex.: [[1, 2], [3, 4]] */
    override fun toString(): String =
        dados.joinToString(prefix = "[", postfix = "]", separator = ", ") { linha ->
            linha.joinToString(prefix = "[", postfix = "]", separator = ", ")
        }

    /** Compara conteúdo (não identidade). Não usa data class, conforme pedido. */
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is Matriz2D) return false
        return dados == other.dados
    }

    override fun hashCode(): Int = dados.hashCode()
}

// Multiplicação por constante à esquerda: 2 * a (extensão de Int).
operator fun Int.times(matriz: Matriz2D): Matriz2D = matriz * this

// --------------------------------------------------------------------------- //
// Casos de teste sugeridos pelo enunciado
// --------------------------------------------------------------------------- //
fun main() {
    val a = Matriz2D(listOf(listOf(1, 2), listOf(3, 4)))
    val b = Matriz2D(listOf(listOf(0, 1), listOf(1, 0)))

    println("a            = $a")            // [[1, 2], [3, 4]]
    println("a + b        = ${a + b}")      // [[1, 3], [4, 4]]
    println("a - b        = ${a - b}")      // [[1, 1], [2, 4]]
    println("a * b        = ${a * b}")      // [[2, 1], [4, 3]]
    println("2 * a        = ${2 * a}")      // [[2, 4], [6, 8]]
    println("a * 3        = ${a * 3}")      // [[3, 6], [9, 12]]
    println("a.transpor() = ${a.transpor()}") // [[1, 3], [2, 4]]
    println("a[0, 1]      = ${a[0, 1]}")    // 2
    println("a.det()      = ${a.det()}")    // -2
    println("a == cópia   = ${a == Matriz2D(listOf(listOf(1, 2), listOf(3, 4)))}") // true
    println("a == b       = ${a == b}")     // false

    // Transposição de matriz 2x3
    val c = Matriz2D(listOf(listOf(1, 2, 3), listOf(4, 5, 6)))
    println("c            = $c")            // [[1, 2, 3], [4, 5, 6]]
    println("c.transpor() = ${c.transpor()}") // [[1, 4], [2, 5], [3, 6]]

    // Tratamento de exceções
    fun esperarErro(rotulo: String, bloco: () -> Unit) {
        try {
            bloco()
            println("$rotulo -> NÃO lançou exceção (inesperado)")
        } catch (e: Exception) {
            println("$rotulo -> ${e::class.simpleName}: ${e.message}")
        }
    }

    esperarErro("linhas de tamanhos diferentes") {
        Matriz2D(listOf(listOf(1, 2), listOf(3)))
    }
    esperarErro("soma com dimensões diferentes") { a + c }
    esperarErro("multiplicação incompatível") {
        a * Matriz2D(listOf(listOf(1, 2, 3)))
    }
    esperarErro("índice fora dos limites") { a[5, 5] }
    esperarErro("det de matriz não 2x2") { c.det() }
}
