import random
from dataclasses import dataclass
from typing import List, Dict, Optional
from collections import defaultdict

import streamlit as st
import pandas as pd

# ==============================
# Data model
# ==============================

@dataclass
class Team:
    name: str
    confed: str   # AFC, CAF, CONCACAF, CONMEBOL, OFC, UEFA, PLAYOFF
    pot: int      # 1..4


# --- Lista de equipos según el documento FIFA ---

teams: List[Team] = [
    # Pot 1
    Team("Mexico",      "CONCACAF", 1),
    Team("Canada",      "CONCACAF", 1),
    Team("USA",         "CONCACAF", 1),
    Team("Spain",       "UEFA",     1),
    Team("Argentina",   "CONMEBOL", 1),
    Team("France",      "UEFA",     1),
    Team("England",     "UEFA",     1),
    Team("Brazil",      "CONMEBOL", 1),
    Team("Portugal",    "UEFA",     1),
    Team("Netherlands", "UEFA",     1),
    Team("Belgium",     "UEFA",     1),
    Team("Germany",     "UEFA",     1),

    # Pot 2
    Team("Croatia",        "UEFA",     2),
    Team("Morocco",        "CAF",      2),
    Team("Colombia",       "CONMEBOL", 2),
    Team("Uruguay",        "CONMEBOL", 2),
    Team("Switzerland",    "UEFA",     2),
    Team("Japan",          "AFC",      2),
    Team("Senegal",        "CAF",      2),
    Team("IR Iran",        "AFC",      2),
    Team("Korea Republic", "AFC",      2),
    Team("Ecuador",        "CONMEBOL", 2),
    Team("Austria",        "UEFA",     2),
    Team("Australia",      "AFC",      2),

    # Pot 3
    Team("Norway",        "UEFA",     3),
    Team("Panama",        "CONCACAF", 3),
    Team("Egypt",         "CAF",      3),
    Team("Algeria",       "CAF",      3),
    Team("Scotland",      "UEFA",     3),
    Team("Paraguay",      "CONMEBOL", 3),
    Team("Tunisia",       "CAF",      3),
    Team("Cote d'Ivoire", "CAF",      3),
    Team("Uzbekistan",    "AFC",      3),
    Team("Qatar",         "AFC",      3),
    Team("Saudi Arabia",  "AFC",      3),
    Team("South Africa",  "CAF",      3),

    # Pot 4
    Team("Jordan",               "AFC",      4),
    Team("Cape Verde",           "CAF",      4),
    Team("Ghana",                "CAF",      4),
    Team("Curacao",              "CONCACAF", 4),
    Team("Haiti",                "CONCACAF", 4),
    Team("New Zealand",          "OFC",      4),
    Team("UEFA PO A winner",     "UEFA",     4),
    Team("UEFA PO B winner",     "UEFA",     4),
    Team("UEFA PO C winner",     "UEFA",     4),
    Team("UEFA PO D winner",     "UEFA",     4),
    Team("Inter-conf playoff 1", "PLAYOFF",  4),
    Team("Inter-conf playoff 2", "PLAYOFF",  4),
]

# 12 grupos: A..L
GROUP_LETTERS = [chr(ord("A") + i) for i in range(12)]


# ==============================
# Helpers de sorteo
# ==============================

def group_teams_by_pot(teams: List[Team]) -> Dict[int, List[Team]]:
    by_pot: Dict[int, List[Team]] = defaultdict(list)
    for t in teams:
        by_pot[t.pot].append(t)
    return by_pot


def can_place(team: Team, group: List[Team]) -> bool:
    """
    Reglas de confederación por grupo:
    - Máx. 1 selección por confederación,
      excepto UEFA que permite hasta 2.
    - PLAYOFF cuenta como confederación (no puede repetirse).
    """
    if len(group) >= 4:
        return False

    confeds = [t.confed for t in group]

    if team.confed == "UEFA":
        if confeds.count("UEFA") >= 2:
            return False
    else:
        if team.confed in confeds:
            return False

    return True


def min_uefa_ok(groups: Dict[str, List[Team]]) -> bool:
    """
    Cada grupo debe tener al menos una selección UEFA.
    """
    for g in GROUP_LETTERS:
        confeds = [t.confed for t in groups[g]]
        if confeds.count("UEFA") < 1:
            return False
    return True


def draw_world_cup(seed: Optional[int] = None) -> Dict[str, List[Team]]:
    """
    Realiza un sorteo completo respetando:
    - 1 equipo por bombo por grupo
    - Máx. 1 equipo por confederación (excepto UEFA, hasta 2)
    - PLAYOFF cuenta como confederación
    - Al menos 1 UEFA por grupo
    - México A, Canadá B, USA D como cabezas de serie fijas
    """
    if seed is not None:
        random.seed(seed)

    by_pot = group_teams_by_pot(teams)
    groups: Dict[str, List[Team]] = {g: [] for g in GROUP_LETTERS}

    # Anfitriones fijos
    host_groups = {"Mexico": "A", "Canada": "B", "USA": "D"}
    pot1_remaining: List[Team] = []

    for t in by_pot[1]:
        if t.name in host_groups:
            groups[host_groups[t.name]].append(t)
        else:
            pot1_remaining.append(t)

    pot_lists = {
        1: pot1_remaining,
        2: list(by_pot[2]),
        3: list(by_pot[3]),
        4: list(by_pot[4]),
    }

    for p in pot_lists:
        random.shuffle(pot_lists[p])

    def backtrack(pot: int, idx: int) -> bool:
        if pot > 4:
            # todos colocados -> verificamos regla de UEFA
            return min_uefa_ok(groups)

        pot_list = pot_lists[pot]
        if idx >= len(pot_list):
            return backtrack(pot + 1, 0)

        team = pot_list[idx]
        group_order = GROUP_LETTERS[:]
        random.shuffle(group_order)

        for g in group_order:
            # 1 equipo de cada bombo por grupo
            if any(t.pot == pot for t in groups[g]):
                continue
            if can_place(team, groups[g]):
                groups[g].append(team)
                if backtrack(pot, idx + 1):
                    return True
                groups[g].pop()

        return False

    if not backtrack(1, 0):
        raise RuntimeError("No se encontró un sorteo válido (muy raro).")

    return groups


def assign_positions(groups: Dict[str, List[Team]]) -> Dict[str, Dict[str, Team]]:
    """
    Asigna:
      Bombo 1 -> posición 1 (A1, B1, ...)
      Bombo 2 -> posición 2
      Bombo 3 -> posición 3
      Bombo 4 -> posición 4
    """
    result: Dict[str, Dict[str, Team]] = {}

    for g in GROUP_LETTERS:
        group_teams = groups[g]
        by_pot: Dict[int, List[Team]] = defaultdict(list)
        for t in group_teams:
            by_pot[t.pot].append(t)

        pos_map: Dict[str, Team] = {}
        for pot in range(1, 5):
            lst = by_pot[pot]
            if len(lst) != 1:
                raise RuntimeError(f"Grupo {g} no tiene exactamente 1 equipo de bombo {pot}")
            team = lst[0]
            label = f"{g}{pot}"
            pos_map[label] = team

        result[g] = pos_map

    return result


# ==============================
# Construir DataFrame para mostrar
# ==============================

def groups_to_dataframe(groups_with_pos: Dict[str, Dict[str, Team]]) -> pd.DataFrame:
    """
    Devuelve un DataFrame con columnas:
    Grupo, Posición, Equipo, Confederación, Bombo
    """
    rows = []
    for g in GROUP_LETTERS:
        for pos in range(1, 5):
            key = f"{g}{pos}"
            t = groups_with_pos[g][key]
            rows.append({
                "Grupo": g,
                "Posición": f"{g}{pos}",
                "Equipo": t.name,
                "Confederación": t.confed,
                "Bombo": t.pot,
            })
    df = pd.DataFrame(rows)
    return df


# ==============================
# APP STREAMLIT
# ==============================

st.set_page_config(page_title="Sorteo Mundial 2026", layout="wide")

st.title("⚽ Simulador de Sorteo – Copa Mundial de la FIFA 2026™")
st.write(
    """
Simulador del sorteo de grupos con las siguientes reglas:

- 12 grupos (A–L) de 4 equipos  
- 4 bombos (1–4), un equipo por bombo en cada grupo  
- México (A1), Canadá (B1) y USA (D1) como anfitriones fijos  
- Máx. 1 selección por confederación en cada grupo  
  (salvo UEFA, que permite hasta 2)  
- PLAYOFF se trata como una confederación más (no se puede repetir)  
- Cada grupo tiene al menos una selección UEFA
    """
)

st.markdown("---")

col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("Control de sorteo")
    use_seed = st.checkbox("Usar semilla fija (reproducible)", value=False)
    seed_value = None
    if use_seed:
        seed_value = st.number_input("Semilla", min_value=0, max_value=10_000, value=42, step=1)

    sortear = st.button("🎲 Sortear grupos")


if sortear:
    try:
        groups = draw_world_cup(seed=seed_value)
        groups_with_pos = assign_positions(groups)
        df = groups_to_dataframe(groups_with_pos)

        with col2:
            st.subheader("Resultado del sorteo")
            # Mostrar tabla completa
            st.dataframe(df, use_container_width=True)

        st.markdown("### Detalle por grupo")

        # Mostrar grupo por grupo
        for g in GROUP_LETTERS:
            st.markdown(f"#### Grupo {g}")
            sub_df = df[df["Grupo"] == g].sort_values("Posición")
            st.table(sub_df[["Posición", "Equipo", "Confederación", "Bombo"]])

    except RuntimeError as e:
        st.error(f"Ocurrió un problema al generar el sorteo: {e}")
else:
    with col2:
        st.info("Haz clic en **🎲 Sortear grupos** para generar un sorteo.")
