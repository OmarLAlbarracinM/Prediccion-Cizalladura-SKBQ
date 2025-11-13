# Predicción de vientos — SKBQ (METAR)

**Propósito**
Modelo predictivo de condiciones de viento y detección temprana de eventos críticos (ej. cizalladura) para el Aeropuerto Internacional Ernesto Cortissoz (SKBQ) usando series históricas METAR.

**Estado**: WIP — prototipo de ingestión, preprocesamiento y modelos baseline (persistence, XGBoost, LSTM).

---

## Contenido rápido

* `data/` — raw, staged, processed (los datos crudos no se guardan en Git; se versionan con DVC).
* `docs/` — diagramas, data dictionary y decisiones de diseño - análisis exploratorio y pruebas reproductibles.
* `.dvc/`, `dvc.yaml` — pipeline y metadatos DVC.

---

## Requisitos

* Python 3.9+ (recomendado 3.10)
* pip / conda
* dvc (instalación básica para local): `pip install dvc`
* pandas, pyarrow (si conviertes a parquet), scikit-learn, xgboost, torch/keras (si usas LSTM), jupyterlab.

Ejemplo (virtualenv):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Datos (clave)

* Archivo principal (ejemplo): `data/raw/DATOS_CRUDOS.csv`
* **No comitees datos grandes** en Git. Usar DVC con remote local (disco o NAS).
* Flujo recomendado:

  1. `dvc init` (una sola vez)
  2. `dvc remote add -d localremote /ruta/al/remote`  # remote local
  3. `dvc add data/raw/DATOS_CRUDOS.csv`
  4. `git add data/raw/DATOS_CRUDOS.csv.dvc .gitignore && git commit -m "track datos crudos via dvc"`
  5. `dvc push`

**Si clonas el repo en otra máquina:**

```bash
git clone <repo>
dvc remote modify localremote path /ruta/del/remote/en/esta/maquina  # si difiere
dvc pull
```

---