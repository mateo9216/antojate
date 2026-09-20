# Copyright (c) 2026, Avantive
# For license information, please see license.txt

"""Pruebas de las firmas de Wompi.

Son funciones puras y son el punto donde un error se paga caro: una firma mal
armada hace que Wompi rechace todos los cobros, y un checksum mal validado
dejaría entrar eventos falsos que marcarían pedidos como pagados.
"""

import hashlib

from frappe.tests import UnitTestCase

from antojate.api.pagos import checksum_esperado, firma_de_integridad


class TestFirmaDeIntegridad(UnitTestCase):
	def test_reproduce_el_ejemplo_oficial_de_wompi(self):
		"""El caso publicado en docs.wompi.co, verbatim.

		Si esta prueba falla, el orden de concatenación se rompió.
		"""
		self.assertEqual(
			firma_de_integridad(
				"sk8-438k4-xmxm392-sn2m249",
				"0000",
				"COP",
				"prod_integrity_Z5mMke9x0k8gpErbDqwrJXMqsI6SFli6",
			),
			"37c8407747e595535433ef8f6a811d853cd943046624a0ec04662b17bbf33bf5",
		)

	def test_el_orden_importa(self):
		"""Cambiar el orden tiene que dar otra firma."""
		correcta = firma_de_integridad("REF-1", 150000, "COP", "secreto")
		invertida = hashlib.sha256(b"150000REF-1COPsecreto").hexdigest()
		self.assertNotEqual(correcta, invertida)

	def test_un_monto_distinto_cambia_la_firma(self):
		"""Esto es lo que impide que alguien edite el precio en la URL."""
		self.assertNotEqual(
			firma_de_integridad("REF-1", 150000, "COP", "secreto"),
			firma_de_integridad("REF-1", 100, "COP", "secreto"),
		)


class TestChecksumDelEvento(UnitTestCase):
	def _evento(self, estado="APPROVED", monto=4490000, timestamp=1530291411):
		return {
			"event": "transaction.updated",
			"data": {
				"transaction": {
					"id": "1234-1610641025-49201",
					"status": estado,
					"amount_in_cents": monto,
					"reference": "REF-1",
				}
			},
			"timestamp": timestamp,
			"signature": {
				"properties": [
					"transaction.id",
					"transaction.status",
					"transaction.amount_in_cents",
				],
				"checksum": "",
			},
		}

	def test_usa_las_propiedades_que_el_evento_declara(self):
		"""Las propiedades se leen del evento, no se asumen fijas.

		Wompi puede cambiar qué campos firma; si las tuviéramos quemadas, el
		día que cambien dejaríamos de validar correctamente.
		"""
		evento = self._evento()
		esperado = hashlib.sha256(
			b"1234-1610641025-49201APPROVED44900001530291411" + b"mi_secreto"
		).hexdigest()
		self.assertEqual(checksum_esperado(evento, "mi_secreto"), esperado)

	def test_cambiar_el_estado_invalida_el_checksum(self):
		"""Un atacante que cambie DECLINED por APPROVED no puede refirmar."""
		aprobado = checksum_esperado(self._evento("APPROVED"), "mi_secreto")
		rechazado = checksum_esperado(self._evento("DECLINED"), "mi_secreto")
		self.assertNotEqual(aprobado, rechazado)

	def test_cambiar_el_monto_invalida_el_checksum(self):
		self.assertNotEqual(
			checksum_esperado(self._evento(monto=4490000), "mi_secreto"),
			checksum_esperado(self._evento(monto=100), "mi_secreto"),
		)

	def test_otro_secreto_da_otro_checksum(self):
		"""Sin el secreto de eventos no se puede falsificar una confirmación."""
		self.assertNotEqual(
			checksum_esperado(self._evento(), "mi_secreto"),
			checksum_esperado(self._evento(), "secreto_del_atacante"),
		)
