# Real source-comparison case study: Titanic inquiries (1912)

The example in `examples/titanic_inquiry_comparison.py` compares two separately
conducted official investigations into the loss of the Titanic:

1. **U.S. Senate Report No. 806**, submitted 28 May 1912 by the Senate Committee
   on Commerce. The official Senate scan is available at
   https://www.senate.gov/about/resources/pdf/TitanicReport.pdf
2. **British Wreck Commissioner's Court report**, dated 30 July 1912. The
   transcript of the court's findings is available at
   https://www.titanicinquiry.org/BOTInq/BOTReport/botRepFindings.php
   The Smithsonian catalogue identifies the original British report as
   Parliamentary Paper Cd. 6352 and lists call number VK1225.T617 1912:
   https://www.si.edu/object/loss-steamship-titanic-report-formal-investigation-circumstances-attending-foundering-april-15-1912%3Asiris_sil_343124

## Recorded differences

| Question | U.S. Senate report | British court report | Stored relation |
|---|---:|---:|---|
| Total lifeboat capacity | 1,176 (printed p. 13) | 1,178 (Findings, Q5(d)) | supports / contradicts |
| People saved or rescued | 706 (printed p. 13) | 712 (Findings, Q21(a)) | supports / contradicts |

The U.S. Senate report's lifeboat-capacity section states 1,176 and gives 706
saved. The British court's findings calculate 1,178 total places and state that
712 people were rescued by Carpathia. The example preserves these source
statements and their locators rather than choosing one figure.

## Methodological limits

- These are two separately conducted government inquiries, not two independent
  eyewitnesses. Their evidence bases may overlap through witnesses, ship records,
  and testimony; independence of the underlying evidence has not been audited.
- The terms "saved" and "rescued" and the reports' counting procedures should be
  checked against the original tables before attempting to reconcile the totals.
- The relation labels in the example are researcher-entered descriptions of how
  each excerpt relates to a narrowly stated numerical claim. They are not
  automated truth labels.
- Neither report is treated as automatically correct. A difference is a prompt
  for source criticism, not proof that one inquiry was dishonest or mistaken.

Run the example:

~~~bash
python examples/titanic_inquiry_comparison.py
~~~

The test `tests/test_titanic_inquiry_comparison.py` checks that both accounts,
short exact quotations, and citation locations remain in the rendered report.
