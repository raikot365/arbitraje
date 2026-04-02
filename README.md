# Arbitrage Monitor Pro v1.0.0 📈

Una herramienta de monitoreo de arbitraje financiero y cripto en tiempo real para el mercado argentino. Compara brechas entre Dólar Oficial, MEP y USDT en múltiples exchanges y entidades bancarias.

## ✨ Características

- **Monitoreo Multimercado:** - **USDT vs USDT:** Arbitraje entre exchanges cripto.
  - **OFICIAL vs OFICIAL:** Comparativa entre entidades bancarias.
  - **OFICIAL vs USDT (Rulo):** Compra en banco y venta en cripto.
  - **MEP vs USDT:** Arbitraje entre dólar bolsa y cripto.
  - **OFICIAL vs MEP:** El "rulo" clásico (Compra oficial, venta MEP). Actualmente con restricción del BCRA (No es posible operar ambos)
- **Cálculo de Bridge (Puente):** Calcula automáticamente el costo de conversión de USD a USDT usando el mejor exchange disponible.
- **Alertas de Telegram:** Notificaciones automáticas cuando se supera el umbral de ganancia configurado.

## 🚀 Instalación (Para Usuarios)

Si solo quieres usar la aplicación, sigue estos pasos:

1. Ve a la sección de [Releases](https://github.com/raikot365/arbitraje/releases) y descarga el archivo `arbitraje.exe`.
2. Crea una carpeta nueva y coloca el `.exe` dentro.
3. Crea un archivo de texto en esa misma carpeta llamado `.env`.
4. Abre el archivo `.env` con el bloc de notas y pega lo siguiente (completando con tus datos):
   ```text
   TELEGRAM_TOKEN=tu_token_de_bot_aqui
   CHAT_ID=tu_chat_id_aqui
