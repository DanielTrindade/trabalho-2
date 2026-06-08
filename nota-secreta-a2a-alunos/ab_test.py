from __future__ import annotations

"""A/B test: llm_agent_v2.py (v2) vs llm_agent.py (v1) no mesmo jogo.

Sobe o serviço LLM uma vez e roda N partidas. Em cada partida coloca
3 instâncias da v2 e 3 da v1, alternando quais posições recebem cada versão
entre as partidas (para anular o viés da ordem do rodízio de narrador, já que
quem narra mais tende a pontuar menos). No fim reporta quantas partidas cada
versão venceu e a pontuação média por versão.

Uso:
    python ab_test.py --model Phi-3.5-mini-instruct.Q4_K_M.gguf --games 10

Importante: aborta se o serviço LLM subir em modo mock — um A/B em mock não
mede nada, pois as respostas semânticas viram constantes.
"""

import argparse
import asyncio
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import aiohttp

ROOT = Path(__file__).resolve().parent

V1_SCRIPT = "llm_agent.py"
V2_SCRIPT = "llm_agent_v2.py"


def find_free_port(start_port: int, host: str = "127.0.0.1", max_tries: int = 300) -> int:
    for port in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"Nenhuma porta livre encontrada a partir de {start_port}")


async def wait_http(url: str, timeout: float = 300.0) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return
        except Exception:
            pass
        await asyncio.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {url}")


async def get_json(url: str) -> Dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()


async def register_agent(game_master_url: str, name: str, url: str) -> None:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{game_master_url.rstrip('/')}/register",
            json={"name": name, "url": url, "kind": "strategic"},
        ) as resp:
            resp.raise_for_status()


def spawn(cmd: List[str]) -> subprocess.Popen[str]:
    # Silencia a saída barulhenta dos servidores; só queremos o placar final.
    return subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def play_one_game(
    llm_url: str,
    versions: List[str],
    db: str,
    base_port: int,
) -> Tuple[int, List[int]]:
    """Sobe um Game Master + 6 agentes (segundo `versions`), joga e devolve
    (winner_idx, final_scores). Encerra GM e agentes ao final."""
    processes: List[subprocess.Popen[str]] = []
    try:
        gm_port = find_free_port(base_port)
        game_master_url = f"http://127.0.0.1:{gm_port}"
        gm_cmd = [
            sys.executable, str(ROOT / "game_master.py"),
            "--port", str(gm_port), "--db", db,
            "--target-score", "30", "--log-dir", str(ROOT / "logs"),
        ]
        processes.append(spawn(gm_cmd))
        await wait_http(f"{game_master_url}/health")

        used_ports = {gm_port}
        next_port = gm_port + 1
        for idx, version in enumerate(versions, start=1):
            port = find_free_port(next_port)
            while port in used_ports:
                port = find_free_port(port + 1)
            used_ports.add(port)
            next_port = port + 1

            script = V2_SCRIPT if version == "v2" else V1_SCRIPT
            name = f"{version}_{idx}"
            agent_url = f"http://127.0.0.1:{port}"
            cmd = [
                sys.executable, str(ROOT / script), game_master_url,
                "--port", str(port), "--llm-url", llm_url, "--name", name,
            ]
            processes.append(spawn(cmd))
            await wait_http(f"{agent_url}/health")
            await register_agent(game_master_url, name=name, url=agent_url)

        timeout = aiohttp.ClientTimeout(total=1200)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{game_master_url}/play") as resp:
                resp.raise_for_status()
                result = await resp.json()
        return int(result["winner"]), list(result["final_scores"])
    finally:
        for proc in reversed(processes):
            if proc.poll() is None:
                proc.terminate()
        for proc in reversed(processes):
            if proc.poll() is None:
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()


async def main() -> None:
    global V1_SCRIPT, V2_SCRIPT
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None, help="Caminho do .gguf. Sem isso, sobe mock e o teste aborta.")
    parser.add_argument("--games", type=int, default=10)
    parser.add_argument("--db", default=str(ROOT / "brazilian_songs.csv"))
    parser.add_argument("--llm-max-concurrency", type=int, default=1)
    parser.add_argument("--baseline", default=V1_SCRIPT, help="Arquivo do agente baseline (rótulo v1).")
    parser.add_argument("--challenger", default=V2_SCRIPT, help="Arquivo do agente desafiante (rótulo v2).")
    parser.add_argument("--allow-mock", action="store_true",
                        help="Permite rodar mesmo em modo mock (apenas para depurar a infra).")
    args = parser.parse_args()

    V1_SCRIPT = args.baseline
    V2_SCRIPT = args.challenger
    print(f"[ab_test] v1 (baseline)  = {V1_SCRIPT}")
    print(f"[ab_test] v2 (desafiante) = {V2_SCRIPT}")

    llm_proc: subprocess.Popen[str] | None = None
    try:
        llm_port = find_free_port(9000)
        llm_url = f"http://127.0.0.1:{llm_port}"
        llm_cmd = [
            sys.executable, str(ROOT / "llm_service.py"),
            "--port", str(llm_port),
            "--max-concurrency", str(args.llm_max_concurrency),
        ]
        if args.model:
            llm_cmd.extend(["--model", args.model])
        else:
            llm_cmd.append("--force-mock")

        print(f"[ab_test] Subindo serviço LLM em {llm_url} (pode levar ~1 min para carregar o modelo)...")
        llm_proc = spawn(llm_cmd)
        await wait_http(f"{llm_url}/health", timeout=600)

        health = await get_json(f"{llm_url}/health")
        mode = health.get("mode")
        print(f"[ab_test] Modo do LLM: {mode}")
        if mode == "mock" and not args.allow_mock:
            print("\n[ab_test] ABORTADO: o LLM subiu em modo MOCK — um A/B aqui não mede nada.")
            print("  Verifique o caminho do --model e se 'llama-cpp-python' está instalado.")
            print("  (Use --allow-mock só se quiser testar a infra do próprio ab_test.)")
            return

        wins = {"v1": 0, "v2": 0}
        score_sum = {"v1": 0, "v2": 0}
        score_n = {"v1": 0, "v2": 0}

        pattern_a = ["v2", "v1", "v2", "v1", "v2", "v1"]
        pattern_b = ["v1", "v2", "v1", "v2", "v1", "v2"]

        for game_idx in range(args.games):
            versions = pattern_a if game_idx % 2 == 0 else pattern_b
            winner_idx, scores = await play_one_game(llm_url, versions, args.db, base_port=8000)

            winner_version = versions[winner_idx]
            wins[winner_version] += 1
            for pos, version in enumerate(versions):
                score_sum[version] += scores[pos]
                score_n[version] += 1

            layout = "".join("2" if v == "v2" else "1" for v in versions)
            print(
                f"Jogo {game_idx + 1:>2}: vencedor={winner_version} (pos {winner_idx}) "
                f"| layout v{layout} | scores={scores}"
            )

        n = args.games
        avg_v2 = score_sum["v2"] / max(1, score_n["v2"])
        avg_v1 = score_sum["v1"] / max(1, score_n["v1"])
        print("\n================ RESULTADO A/B ================")
        print(f"  v2 (otimizada): venceu {wins['v2']:>2}/{n}  | pontuação média {avg_v2:.2f}")
        print(f"  v1 (baseline) : venceu {wins['v1']:>2}/{n}  | pontuação média {avg_v1:.2f}")
        print("==============================================")
        if wins["v2"] > wins["v1"]:
            print("  => v2 venceu o confronto direto. Vale incorporar no llm_agent.py.")
        elif wins["v2"] < wins["v1"]:
            print("  => v2 NÃO superou a v1. Melhor descartar/revisar (possível overfitting).")
        else:
            print("  => Empate em vitórias. Olhe a pontuação média para desempatar.")
    finally:
        if llm_proc is not None and llm_proc.poll() is None:
            llm_proc.terminate()
            try:
                llm_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                llm_proc.kill()


if __name__ == "__main__":
    asyncio.run(main())
