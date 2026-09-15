import unittest

from app import ExplainRequest


class ExplainRequestContractTests(unittest.TestCase):
    def test_existing_spring_contract_still_works(self) -> None:
        request = ExplainRequest.model_validate(
            {
                "invoice": {"invoiceNumber": "INV-1"},
                "invoiceqError": {"httpStatus": 400},
                "question": "Why did it fail?",
            }
        )

        self.assertEqual(request.invoice, {"invoiceNumber": "INV-1"})
        self.assertEqual(request.invoiceqError, {"httpStatus": 400})

    def test_explicit_request_response_names_are_accepted(self) -> None:
        request = ExplainRequest.model_validate(
            {
                "requestJson": {"invoiceNumber": "INV-2"},
                "responseJson": {"httpStatus": 400},
                "question": "What does this error mean?",
            }
        )

        self.assertEqual(request.invoice, {"invoiceNumber": "INV-2"})
        self.assertEqual(request.invoiceqError, {"httpStatus": 400})


if __name__ == "__main__":
    unittest.main()
