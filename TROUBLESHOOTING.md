# 🔧 Troubleshooting - Solución de Problemas

## Error Común: "Cannot import 'setuptools.build_meta'"

### Síntomas
```
ERROR: BackendUnavailable: Cannot import 'setuptools.build_meta'
ERROR: No se pudieron instalar las dependencias
```

### Solución Rápida

#### Opción 1: Usar el script de instalación corregido
```cmd
setup_fixed.bat
```

Este script:
1. Elimina el entorno virtual corrupto
2. Crea uno nuevo limpio
3. Actualiza pip, setuptools y wheel
4. Instala dependencias sin caché

#### Opción 2: Instalación manual paso a paso

```cmd
# 1. Eliminar entorno virtual anterior
rmdir /s /q venv

# 2. Crear nuevo entorno virtual
python -m venv venv

# 3. Activar entorno
venv\Scripts\activate

# 4. Actualizar herramientas base
python -m pip install --upgrade pip setuptools wheel

# 5. Instalar dependencias mínimas
pip install -r requirements_minimal.txt
```

#### Opción 3: Instalación una por una (más lento pero seguro)

```cmd
venv\Scripts\activate

python -m pip install --upgrade pip setuptools wheel

pip install numpy
pip install pandas
pip install scikit-learn
pip install xgboost
pip install pyyaml
pip install python-dotenv
pip install loguru
pip install sqlalchemy
pip install requests
pip install beautifulsoup4
pip install APScheduler
pip install pytest
```

---

## Otros Errores Comunes

### Error: "ModuleNotFoundError: No module named 'src'"

**Causa:** Ejecutando desde directorio incorrecto

**Solución:**
```cmd
cd C:\Users\Leonardo\Documents\apostacion
python daily_bot.py
```

---

### Error: "FileNotFoundError: models/soccer_model.pkl"

**Causa:** Modelos no entrenados

**Solución:**
```cmd
python src/models/train_model.py
```

O simplemente ejecuta `daily_bot.py` - entrenará automáticamente.

---

### Error: "PermissionError" en logs

**Causa:** Archivo de log abierto en otro programa

**Solución:**
1. Cierra todos los editores de texto
2. Reinicia el terminal
3. O borra `logs/triunfobet_bot.log`

---

### Error: "yaml.scanner.ScannerError"

**Causa:** Error de sintaxis en config.yaml

**Solución:**
1. Revisa la indentación (debe ser espacios, no tabs)
2. Restaura desde backup:
```cmd
git checkout config/config.yaml
```

---

### Error: Import error con xgboost en Windows

**Causa:** Falta compilador de C++

**Solución:**

1. Instala Visual C++ Redistributable:
   - Descarga: https://aka.ms/vs/17/release/vc_redist.x64.exe
   - Instala y reinicia

2. O usa la versión precompilada:
```cmd
pip uninstall xgboost
pip install xgboost --no-cache-dir
```

---

### Warning: "Telegram notifications disabled"

**Causa:** No configuraste credenciales de Telegram (es opcional)

**Solución:**
- Si no quieres Telegram, ignora este warning
- Si quieres Telegram:
  1. Crea bot con @BotFather
  2. Obtén tu chat ID con @userinfobot
  3. Configura en `.env`:
  ```env
  TELEGRAM_BOT_TOKEN=tu_token
  TELEGRAM_CHAT_ID=tu_chat_id
  ```

---

### El bot no encuentra picks con valor

**Causa:** Es normal. No siempre hay apuestas con edge suficiente.

**Solución:**
- Esto es **correcto**
- Es mejor no apostar que forzar picks sin valor
- Si quieres más picks (menos conservador):
  - Edita `config/config.yaml`
  - Reduce `min_edge` de 0.05 a 0.03
  - Reduce `min_probability` de 0.65 a 0.60

---

### Error: "Database is locked"

**Causa:** Múltiples instancias del bot corriendo

**Solución:**
```cmd
# Mata todos los procesos de Python
taskkill /F /IM python.exe

# O reinicia y ejecuta solo una vez
python daily_bot.py
```

---

### Python no encontrado en PATH

**Causa:** Python no instalado o no en PATH

**Solución:**
1. Reinstala Python desde python.org
2. Durante instalación, marca "Add Python to PATH"
3. Reinicia terminal

---

## Verificación de Instalación

Después de solucionar problemas, verifica:

```cmd
# Verifica Python
python --version

# Verifica pip
pip --version

# Verifica instalación del bot
python verify_installation.py

# Test rápido
python test_all.py
```

---

## Logs de Debug

Si sigues teniendo problemas:

1. **Revisa los logs:**
```cmd
type logs\triunfobet_bot.log
```

2. **Ejecuta con modo debug:**
Edita `config/config.yaml`:
```yaml
logging:
  level: "DEBUG"  # Cambiar de INFO a DEBUG
```

3. **Ejecuta test individual:**
```cmd
# Test el componente que falla
python src/scrapers/triunfobet_scraper.py
python src/models/train_model.py
```

---

## Contacto para Soporte

Si ninguna solución funciona:

1. Revisa el `README.md` completo
2. Revisa `EXAMPLES.md` para ejemplos
3. Verifica versión de Python: debe ser 3.10+
4. Asegúrate de tener al menos 2GB de RAM libre
5. Verifica que tengas permisos de escritura en el directorio

---

## Reinstalación Completa (Último Recurso)

```cmd
# 1. Backup de configuración
copy .env .env.backup
copy config\config.yaml config\config.yaml.backup

# 2. Eliminar todo
rmdir /s /q venv
rmdir /s /q data
rmdir /s /q models
rmdir /s /q logs

# 3. Instalación limpia
setup_fixed.bat

# 4. Restaurar configuración
copy .env.backup .env

# 5. Verificar
python verify_installation.py
```

---

## Compatibilidad

### Versiones Probadas
- ✅ Python 3.10
- ✅ Python 3.11
- ✅ Python 3.12
- ✅ Windows 10/11
- ✅ Windows Server 2019+

### No Soportado
- ❌ Python 3.9 o inferior
- ❌ Python 2.x
- ⚠️  Windows 7 (puede funcionar con limitaciones)

---

## Optimización de Rendimiento

Si el bot es muy lento:

1. **Reduce datos de entrenamiento:**
Edita `src/models/train_model.py`:
```python
soccer_data = generate_training_data("soccer", num_matches=1000)  # Reducir de 2000
```

2. **Usa modelo más simple:**
Edita `config/config.yaml`:
```yaml
model:
  type: "random_forest"  # Más rápido que xgboost
```

3. **Limita matches analizados:**
Modifica `daily_bot.py` si es necesario

---

¿Sigues teniendo problemas? Revisa los logs en `logs/triunfobet_bot.log` para más detalles.
