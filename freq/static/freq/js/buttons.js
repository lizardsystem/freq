/*global $:false, jQuery:false, moment:false, ko:false, fillChart:false, */


function datePickerValue() {
    return {
        start: $('#date_picker_start').val(),
        end: $('#date_picker_end').val()
    };
}


function spinnerValue() {
    return {
        value: $('#spinner').val()
    };
}


function changeGraphs(buttonType, altValue){
    // only change graphs when clicked?
    return function(value){
        if (altValue !==undefined) { value = altValue(); }
        console.log(window.active, buttonType, value);
        console.log(value);
        var queryUrl = '/' + window.active + '_data/?button=' + buttonType +
            '&value=' + JSON.stringify(value);
        loadData(queryUrl, updateGraphs)
    };
}


function updateGraphs(graphs){
    for(var i; i < graphs.length; i++ ){
        var graph = graphs[i];
        d3.select(graph.name).datum(graph.data).call(charts[i])
    }
}


function setDate(startDate, endDate){
    $('#date_picker_start').datepicker('setDate', startDate);
    $('#date_picker_end').datepicker('setDate', endDate);
}


function loadDatePicker(){
    $('.input-daterange').datepicker({
        format: 'dd-mm-yyyy',
        endDate: 'd',
        viewMode: 'years'
    }).change(changeGraphs('datepicker', datePickerValue));
    console.log('updating datepicker');
    setDate(window.startpage.startDate, window.startpage.endDate);
}


function loadSpinner(){
    $('#spinner').spinner().change(changeGraphs('spinner', spinnerValue));
        // hier setTimeout(function() gebruiken! en even checken of
        // het direct werkt. Anders boolean zetten die daarbuiten
        // ook gezet wordt.
}


function clickDropDown(dropdown_id){
    var options = true;
    var i = 0;
    var oldSelected = $('#dropdown-selected');
    var dropdowns = [oldSelected.text()];
    var newText = $('#dropdown-option-' + dropdown_id).text();
    oldSelected.text(newText);
    while(options) {
        var dropdown = $('#dropdown-option-' + i);
        if(dropdown.length) {
            dropdowns.push(dropdown.text());
        } else {
            options = false
        }
        i++;
    }
    dropdowns = dropdowns.slice(0, dropdown_id + 1).concat(
        dropdowns.slice(dropdown_id + 2, dropdowns.length));
    dropdowns.sort();
    for(var i=0; i < dropdowns.length; i++){
        $('#dropdown-option-' + i).text(dropdowns[i])
    }
    changeGraphs('dropdown')({ value: $.trim(newText) });
}


function clickGraphPoint(event){
    changeGraphs('graph')(event[0].point);
}


$(document).ready(
    function() {
        try {loadDatePicker();} catch(e) {
            console.log("No date picker available, date picker not loaded", e);
        }
        try {loadSpinner();} catch(e) {
            console.log("No spinner available, spinner not loaded", e);
        }
        //try {loadDropDownSelector();} catch(e) {
        //    console.log("No selector available, selector not loaded", e);
        //}

    }
);
