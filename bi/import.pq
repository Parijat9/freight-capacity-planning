// Create a text parameter named DataFolder pointing to the generated build directory.
let
    Source = Csv.Document(File.Contents(DataFolder & "/forecast_detail.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {{"week", type number}, {"actual", type number}, {"forecast", type number}, {"lower", type number}, {"upper", type number}, {"covered", type number}}, "en-US")
in
    Typed
