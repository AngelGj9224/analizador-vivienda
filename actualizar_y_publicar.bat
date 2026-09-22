@echo off
cd /d "%~dp0"

echo ============================
echo  1/4 Buscando casas nuevas...
echo ============================
python -m src.main
if errorlevel 1 (
  echo.
  echo Hubo un error en la busqueda. Revisa el mensaje de arriba.
  pause
  exit /b 1
)

echo.
echo ============================
echo  2/4 Generando la pagina...
echo ============================
python -m src.publish
if errorlevel 1 (
  echo.
  echo Hubo un error generando la pagina.
  pause
  exit /b 1
)

echo.
echo ============================
echo  3/4 Guardando cambios (git)...
echo ============================
git add docs/

git diff --cached --quiet
if errorlevel 1 (
  git commit -m "Actualiza publicaciones"
) else (
  echo No hay cambios nuevos que subir esta vez.
  pause
  exit /b 0
)

echo.
echo ============================
echo  4/4 Subiendo a GitHub...
echo ============================
git push
if errorlevel 1 (
  echo.
  echo Hubo un error subiendo a GitHub. Revisa tu conexion o tu sesion de GitHub.
  pause
  exit /b 1
)

echo.
echo Listo! Ya se actualizo https://angelgj9224.github.io/analizador-vivienda/
pause
