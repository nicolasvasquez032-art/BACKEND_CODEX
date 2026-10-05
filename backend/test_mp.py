import mercadopago

sdk = mercadopago.SDK("APP_USR-2359765611894441-100221-3aaf4343fb9546c1ce1dcb0716f0a166-3735144816")

preference_data = {
    "items": [
        {
            "title": "Suscripción TalentMatch PRO (1 mes)",
            "quantity": 1,
            "unit_price": 49.00,
            "currency_id": "USD",
        }
    ],
    "payer": {
        "email": "test@example.com",
    },
    "back_urls": {
        "success": "http://18.191.162.235:8000/pagos/success",
        "failure": "http://18.191.162.235:8000/pagos/failure",
        "pending": "http://18.191.162.235:8000/pagos/pending",
    },
    "auto_return": "approved",
    "external_reference": "test-123",
}

response = sdk.preference().create(preference_data)
print("MP Response:", response)
