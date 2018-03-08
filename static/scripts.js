$(document).ready(function() {
  // form data(playlist name, artist list) -> playlist data, artists Data
  // sends the form data and is retuned the spotify data
  $(function() {
    $('#find-artists').bind('click', function() {
      $.post($SCRIPT_ROOT + '/search_artists',
      $("#search-query").serialize(),
      function(data) {
        console.log(data.artists_data);
        for (i=0; i<data.artists_data.length; i++) {
          $('#search-results').append(data.artists_data[i]['search_term'])
          .append(function() {
            for (k=0; k<data.artists_data[i]['data'].length; k++) {
              '<h1>' + (JSON.stringify(data.artists_data[i]['data'][k])) + '</h1>';
            }
          })
          // $('#search-results').append(JSON.stringify(data.artists_data[0]));
          // console.log(data.artists_data[i]);
        };
      });
      return false;
    });
  });
})
