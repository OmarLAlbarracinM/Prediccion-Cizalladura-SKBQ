"""
Pruebas automatizadas para los endpoints de la API de prediccion de viento SKBO.

Cubren el comportamiento funcional del servicio completo: disponibilidad del servidor,
carga del modelo, estructura del contrato JSON, validez fisica de las predicciones
y manejo correcto de inputs invalidos.

Por defecto apuntan al servicio publico en Render. Para probar una instancia local
(docker compose up), cambiar BASE_URL a "http://localhost:8000".

Ejecucion:
    pip install pytest httpx
    pytest tests/test_predict.py -v
"""

import os
import httpx
import pytest

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Tiempo de espera en segundos. La primera llamada puede tardar si el servicio
# estuvo inactivo mas de 15 minutos (plan gratuito de Render).
TIMEOUT = 120


class TestHealth:
    def test_health_retorna_200(self):
        """
        Verifica que el endpoint /health responde con HTTP 200.
        Confirma que el servidor esta activo y accesible desde la red.
        """
        respuesta = httpx.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert respuesta.status_code == 200

    def test_health_modelo_cargado(self):
        """
        Verifica que el modelo LSTM esta cargado en memoria al momento del health check.
        Si el modelo no cargara durante el startup, este test falla antes de intentar
        cualquier prediccion.
        """
        respuesta = httpx.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        cuerpo = respuesta.json()
        assert cuerpo["status"] == "ok"
        assert cuerpo["model"] == "loaded"

    def test_health_contiene_campos_requeridos(self):
        """
        Verifica que la respuesta de /health incluye todos los campos del contrato:
        status, model, airport y model_version.
        Garantiza que cualquier cliente que dependa de estos campos no recibira
        una respuesta incompleta.
        """
        respuesta = httpx.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        cuerpo = respuesta.json()
        for campo in ("status", "model", "airport", "model_version"):
            assert campo in cuerpo, f"Campo faltante en /health: {campo}"


class TestPredict:
    def test_predict_sin_body_retorna_200(self):
        """
        Verifica que /predict responde con HTTP 200 cuando se llama sin body.
        Este es el modo de uso normal: la API descarga datos de SIMFAC automaticamente
        y no requiere que el cliente envie ninguna observacion.
        """
        respuesta = httpx.post(f"{BASE_URL}/predict", json={}, timeout=TIMEOUT)
        assert respuesta.status_code == 200

    def test_predict_contiene_campos_requeridos(self):
        """
        Verifica que la respuesta de /predict incluye todos los campos del contrato:
        airport, prediction_horizon_hours, wind_direction_deg, wind_speed_kt,
        wind_gust_kt, windshear_alert, forecast, generated_at, model_version
        y data_source.
        Cualquier campo faltante romperia la integracion con sistemas consumidores.
        """
        respuesta = httpx.post(f"{BASE_URL}/predict", json={}, timeout=TIMEOUT)
        cuerpo = respuesta.json()
        campos = (
            "airport",
            "prediction_horizon_hours",
            "wind_direction_deg",
            "wind_speed_kt",
            "wind_gust_kt",
            "windshear_alert",
            "forecast",
            "generated_at",
            "model_version",
            "data_source",
        )
        for campo in campos:
            assert campo in cuerpo, f"Campo faltante en /predict: {campo}"

    def test_predict_horizonte_por_defecto_es_6(self):
        """
        Verifica que cuando no se especifica horizon_hours, el pronostico cubre
        exactamente 6 horas (H+01 a H+06), que es el horizonte operacional
        definido para la DINAV.
        """
        respuesta = httpx.post(f"{BASE_URL}/predict", json={}, timeout=TIMEOUT)
        cuerpo = respuesta.json()
        assert cuerpo["prediction_horizon_hours"] == 6
        assert len(cuerpo["forecast"]) == 6

    def test_predict_horizonte_personalizado(self):
        """
        Verifica que el parametro horizon_hours es respetado correctamente.
        Al pedir 3 horas, el forecast debe tener exactamente 3 pasos.
        Permite a los clientes ajustar el horizonte segun su necesidad operacional.
        """
        respuesta = httpx.post(
            f"{BASE_URL}/predict", json={"horizon_hours": 3}, timeout=TIMEOUT
        )
        cuerpo = respuesta.json()
        assert cuerpo["prediction_horizon_hours"] == 3
        assert len(cuerpo["forecast"]) == 3

    def test_predict_direccion_en_rango_valido(self):
        """
        Verifica que la direccion del viento predicha es fisicamente valida en
        cada hora del horizonte (entre 0 y 360 grados).
        Una direccion fuera de rango indicaria un error en la conversion de
        componentes seno/coseno a grados meteorologicos.
        """
        respuesta = httpx.post(f"{BASE_URL}/predict", json={}, timeout=TIMEOUT)
        cuerpo = respuesta.json()
        for hora in cuerpo["forecast"]:
            assert 0 <= hora["wind_direction_deg"] < 360, (
                f"Direccion fuera de rango en {hora['step']}: {hora['wind_direction_deg']}"
            )

    def test_predict_velocidad_no_negativa(self):
        """
        Verifica que la velocidad del viento predicha no es negativa en ninguna
        hora del horizonte. La velocidad es una magnitud fisica no negativa; un
        valor negativo indicaria un error en el desescalado del modelo.
        """
        respuesta = httpx.post(f"{BASE_URL}/predict", json={}, timeout=TIMEOUT)
        cuerpo = respuesta.json()
        for hora in cuerpo["forecast"]:
            assert hora["wind_speed_kt"] >= 0, (
                f"Velocidad negativa en {hora['step']}: {hora['wind_speed_kt']}"
            )

    def test_predict_forecast_tiene_estructura_correcta(self):
        """
        Verifica que cada hora del array forecast contiene los cinco campos
        esperados: step, wind_direction_deg, wind_speed_kt, windshear y
        windshear_cause. Un campo faltante en cualquier hora romperia la
        lectura del pronostico por parte del cliente.
        """
        respuesta = httpx.post(f"{BASE_URL}/predict", json={}, timeout=TIMEOUT)
        cuerpo = respuesta.json()
        for hora in cuerpo["forecast"]:
            for campo in ("step", "wind_direction_deg", "wind_speed_kt", "windshear", "windshear_cause"):
                assert campo in hora, f"Campo '{campo}' faltante en {hora.get('step', '?')}"

    def test_predict_fuente_de_datos_es_simfac(self):
        """
        Verifica que cuando no se envian observaciones propias, la API descarga
        los datos automaticamente desde SIMFAC y lo refleja en data_source.
        Confirma que el modo automatico esta funcionando correctamente.
        """
        respuesta = httpx.post(f"{BASE_URL}/predict", json={}, timeout=TIMEOUT)
        cuerpo = respuesta.json()
        assert cuerpo["data_source"] == "simfac_api"

    def test_predict_body_invalido_retorna_400_o_422(self):
        """
        Verifica que un valor de horizon_hours fuera del rango permitido (1-12)
        es rechazado con HTTP 400 o 422.
        Comprueba que la validacion de parametros de entrada esta activa y
        protege al modelo de recibir configuraciones invalidas.
        """
        respuesta = httpx.post(
            f"{BASE_URL}/predict",
            json={"horizon_hours": 99},
            timeout=TIMEOUT,
        )
        assert respuesta.status_code in (400, 422)

    def test_predict_metar_insuficientes_retorna_400(self):
        """
        Verifica que enviar menos de 20 observaciones METAR propias retorna
        HTTP 400 con un mensaje descriptivo.
        El modelo LSTM requiere una ventana historica de 20 registros horarios;
        con menos registros la inferencia no es posible.
        """
        respuesta = httpx.post(
            f"{BASE_URL}/predict",
            json={"metar_observations": ["SKBO 190000Z 13005KT 9999 FEW020 14/10 Q1025"]},
            timeout=TIMEOUT,
        )
        assert respuesta.status_code == 400
