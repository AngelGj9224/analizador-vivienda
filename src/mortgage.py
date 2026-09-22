"""
Estimación de mensualidad de crédito Infonavit (Crédito Tradicional),
según los supuestos que diste:

  1) Enganche: $1,000,000 MXN
  2) Salario de $42,000/mes -> por arriba de 6.6 UMA (~$23,537), así que
     te toca la tasa fija más alta del rango 2026: 10.45% anual.
  3) Plazos: 20 y 25 años.

Fuente de la tasa y el tope de crédito (septiembre 2026): rango de tasa
fija 3.69%–10.45% anual según nivel salarial, y crédito tradicional
máximo de $2,935,002.35 — El Imparcial,
https://www.elimparcial.com/dinero/2026/09/17/credito-infonavit-cuanto-presta-que-tasa-tiene-y-cuantos-puntos-necesitas-antes-que-finalice-este-2026/

Esto es una ESTIMACIÓN con la fórmula estándar de amortización (pago fijo
mensual, tasa fija), no incluye seguros ni comisiones, y no sustituye la
precalificación oficial en "Mi Cuenta Infonavit".
"""

DOWN_PAYMENT = 1_000_000.0
ANNUAL_RATE = 0.1045  # 10.45%, tasa más alta del rango 2026 (salario > 6.6 UMA)
TERM_YEARS = (20, 25)
MAX_CREDIT_TRADICIONAL = 2_935_002.35  # tope 2026 del crédito tradicional Infonavit
SALARY = 42_000.0


def monthly_payment(principal: float, annual_rate: float, years: int) -> float:
    """Pago mensual fijo (amortización francesa) para un crédito de
    `principal` a `annual_rate` anual fija, a `years` años."""
    n = years * 12
    r = annual_rate / 12
    if principal <= 0:
        return 0.0
    if r == 0:
        return principal / n
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def estimate(price: float):
    """Devuelve el estimado de crédito/mensualidad para una casa de este
    precio, con los supuestos de arriba. `price` puede ser None."""
    if not price:
        return None

    loan_amount = max(price - DOWN_PAYMENT, 0)
    payments = {
        years: round(monthly_payment(loan_amount, ANNUAL_RATE, years), 2)
        for years in TERM_YEARS
    }

    return {
        "down_payment": DOWN_PAYMENT,
        "loan_amount": round(loan_amount, 2),
        "annual_rate": ANNUAL_RATE,
        "monthly_payments": payments,
        "exceeds_max_credit": loan_amount > MAX_CREDIT_TRADICIONAL,
        "exceeds_salary": {years: p > SALARY for years, p in payments.items()},
    }
