"1. Muuta ylipitkät huutomerkkijonot korkeintaan neljän huutomerkin sarjoiksi
let fix1 = "%s/\(\d\+\t!.*PUNC.*\n.*\)\n.*\(1\t!.*ROOT.*\n.*\n\)\{4,\}\(1\t[^!].*\)/\1\r\2\2\2\3/gc"

let finfix = ".*_.*\n\(\d\+\t!.*PUNC.*\n\)\{4,}"
