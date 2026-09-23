"""
Estimación de mensualidad de crédito Infonavit (Crédito Tradicional),
según los supuestos que diste:

  1) Enganche: $1,000,000 MXN, pero antes de aplicarlo al precio se le
     descuentan los gastos de escrituración estimados (ISAI, notario,
     registro, avalúo) — típicamente 4%-9% del valor de la propiedad;
     se usa 6% como estimado intermedio. O sea: no todo el enganche baja
     el precio, una parte se la comen los gastos de escrituración.
  2) Salario de $42,000/mes -> por arriba de 6.6 UMA (~$23,537), así que
     te toca la tasa fija más alta del rango 2026: 10.45% anual.
  3) Plazos: 20 y 25 años.
  4) La mensualidad que se muestra ya descuenta la aportación patronal
     (5% de tu salario, obligatoria por ley): una vez que tienes un
     crédito Infonavit activo, ese 5% que tu patrón aporta cada bimestre
     se abona directo al crédito, reduciendo lo que realmente sale de tu
     bolsillo/nómina más allá de eso.

Fuentes:
- Tasa y tope de crédito (septiembre 2026): rango de tasa fija
  3.69%-10.45% anual según nivel salarial, crédito tradicional máximo de
  $2,935,002.35 — El Imparcial,
  https://www.elimparcial.com/dinero/2026/09/17/credito-infonavit-cuanto-presta-que-tasa-tiene-y-cuantos-puntos-necesitas-antes-que-finalice-este-2026/
- Aportación patronal del 5% del SBC, obligatoria y separada del
  descuento de nómina del crédito — Expansión / Ley del Infonavit Art. 29,
  https://expansion.mx/finanzas-personales/2025/01/21/cuanto-aporta-patron-a-tu-cuenta-infonavit
- Las aportaciones patronales posteriores a obtener un crédito se abonan
  al crédito (reducen el saldo/plazo) — Infonavit, "Uso de la subcuenta de
  vivienda",
  https://portalmx.infonavit.org.mx/wps/wcm/connect/2ede00b1-9a34-4496-857d-ee316d889821/Uso_Subcuenta_Vivienda-.pdf
- Gastos de escrituración típicos 4%-9% del valor del inmueble (ISAI
  2%-4.5%, notario 1%-2.5%, registro 0.5%-1.2%, avalúo 0.15%-0.35%) —
  varias fuentes (tuhabi.mx, cotizadorhipotecario.mx, cuantomecuesta.com),
  septiembre 2026.

Esto es una ESTIMACIÓN con la fórmula estándar de amortización (pago fijo
mensual, tasa fija) y un modelo simplificado de aportación patronal — no
incluye seguros ni comisiones, y no sustituye la precalificación oficial
en "Mi Cuenta Infonavit" ni una cotización real de escrituración con un
notario.
"""

DOWN_PAYMENT = 1_000_000.0
ANNUAL_RATE = 0.1045  # 10.45%, tasa más alta del rango 2026 (salario > 6.6 UMA)
TERM_YEARS = (20, 25)
MAX_CREDIT_TRADICIONAL = 2_935_002.35  # tope 2026 del crédito tradicional Infonavit
SALARY = 42_000.0

CLOSING_COSTS_PCT = 0.06  # estimado de gastos de escrituración, % del precio
EMPLOYER_CONTRIBUTION_PCT = 0.05  # aportación patronal, % del salario


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

    closing_costs = price * CLOSING_COSTS_PCT
    effective_down_payment = max(DOWN_PAYMENT - closing_costs, 0)
    loan_amount = max(price - effective_down_payment, 0)

    employer_contribution = round(SALARY * EMPLOYER_CONTRIBUTION_PCT, 2)
    gross_payments = {
        years: round(monthly_payment(loan_amount, ANNUAL_RATE, years), 2)
        for years in TERM_YEARS
    }
    net_payments = {
        years: round(max(p - employer_contribution, 0), 2) for years, p in gross_payments.items()
    }

    return {
        "down_payment": DOWN_PAYMENT,
        "closing_costs": round(closing_costs, 2),
        "effective_down_payment": round(effective_down_payment, 2),
        "loan_amount": round(loan_amount, 2),
        "annual_rate": ANNUAL_RATE,
        "employer_contribution": employer_contribution,
        "monthly_payments_gross": gross_payments,
        "monthly_payments_net": net_payments,
        "exceeds_max_credit": loan_amount > MAX_CREDIT_TRADICIONAL,
        "exceeds_salary": {years: p > SALARY for years, p in net_payments.items()},
    }
