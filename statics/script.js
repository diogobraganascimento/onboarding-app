const form =
    document.getElementById('formRegistro');

if (form) {

    form.addEventListener('submit', function(event) {

        const erroSelecionado =
            document.getElementById(
                'desvio_identificado'
            ).value.trim();

        const novoErro =
            document.getElementById(
                'novo_erro'
            ).value.trim();

        if (
            erroSelecionado === ''
            &&
            novoErro === ''
        ) {

            event.preventDefault();

            alert(
                'Selecione um desvio identificado ou informe um novo.'
            );

        }

    });

}