"""Round 11: assembla backtest/results_round11.md dalle parti (nessun calcolo). python -I -X utf8 backtest/run_round11_final.py"""
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(REPO_ROOT, "backtest", "round11_parts")


def rd(n):
    return open(os.path.join(P, n), encoding="utf-8").read().strip()


head = ("# Round 11 — margine sul mercato (solo backtest)\n\n"
        "**La produzione non è stata toccata.** Criteri nel prereg qui sotto (scritto prima di eseguire le analisi; V5 e V6 aggiunti con il loro prereg prima di calcolarli). "
        "Rilancio: `python -I -X utf8 backtest/run_round11.py [V1|V2|V3]` (V1 con cache in `round11_parts/_v1cache`, `R11_MAXNEW=n` configurazioni per invocazione), "
        "`python -I -X utf8 backtest/run_round11_v56.py` (V5 e V6), poi `run_round11_final.py`.\n\n---\n")
parts = [head, rd("COMMENTO.md"), "\n\n---\n\n# Preregistrazione\n", rd("prereg.md")] + ["\n\n---\n\n" + rd(f"{n}.md") for n in ("V1", "V2", "V3", "V4", "V5", "V6")]
open(os.path.join(REPO_ROOT, "backtest", "results_round11.md"), "w", encoding="utf-8").write("\n".join(parts) + "\n")
print("ok")
