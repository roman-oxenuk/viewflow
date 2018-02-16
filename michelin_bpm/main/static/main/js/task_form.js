$(document).ready(function(){
    let $doneBtn = $('#done-btn')

    console.log('\n')
    console.log('ready!')
    console.log('selected: ', $('[data-correction-field="true"]'))
    console.log('\n')

    $('[data-correction-field="true"]').on('keyup', function(){
        let this_button = $('button[name="' +  $(this).attr('action_btn_name') + '"]')
        if($(this).val().length > 0) {
            $('#michelin-actions button').not(this_button).attr('disabled', 'disabled')
            $('[data-correction-field="true"]').not(this).attr('disabled', 'disabled')
            $(this)
        } else {
            $('#michelin-actions button').attr('disabled', false)
            $('[data-correction-field="true"]').attr('disabled', false)
        }
    });

    $('.field-history-folding').on('click', function(e){
        e.preventDefault()
        $(this).closest('tr').nextUntil('tr:not(.field-history-row)').find('.field-history-data').slideToggle()
    });

    $('.all-history-folding').on('click', function(e){
        e.preventDefault()
        $(this).closest('li').find('.all-history-data').slideToggle()
    });
})