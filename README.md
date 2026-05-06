# RA-Flow v2

RA-Flow v2 is an interactive aerodynamic intelligence MVP that combines geometry ingestion, voxel/SDF preprocessing, a GPU-aware Fourier-style surrogate flow engine, real-time Socket.IO streaming, optimization, and a React/Three.js visualization client.

## Monorepo Layout

```text
.
|-- backend
|-- frontend
|-- models
`-- shared
```

## Backend

The backend exposes a FastAPI API on `http://localhost:8000` and a Flask-SocketIO realtime server on `http://localhost:8001`.

### Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

### Run

```powershell
python -m backend.run
```

## Frontend

### Install

```powershell
cd frontend
npm install
```

### Run

```powershell
npm run dev
```

The frontend expects the backend on port `8000` and Socket.IO on port `8001`.

## Tests

```powershell
pytest backend/tests
npm --prefix frontend test
```

## MVP Features

- STL/OBJ/GLB/GLTF/STEP upload and normalization
- Mesh to voxel grid + SDF preprocessing
- GPU-aware FNO-like surrogate simulation
- Socket.IO streaming of simulation frames
- Drag hotspot and explainability maps
- Iterative geometry optimization
- React Three Fiber viewer with geometry, pressure, streamline, and optimization modes
- Multi-resolution voxel pyramid helper
- Diffusion-inspired shape proposal stub for future generative optimization
