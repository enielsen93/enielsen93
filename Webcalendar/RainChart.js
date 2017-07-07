function drawplotid(starttime,stoptime){
d3.select(".plotid").selectAll('*').remove()
var plotid = d3.select(".plotid"),
    margin = {top: 20, right: 20, bottom: 30, left: 50},
    width = +plotid.attr("width") - margin.left - margin.right,
    height = +plotid.attr("height") - margin.top - margin.bottom,
    g = plotid.append("g").attr("transform", "translate(" + margin.left + "," + margin.top + ")");

var parseTime = d3.timeParse("%Y-%m-%d %H:%M:%S");


var parseTimeInput = d3.timeParse("%Y-%m-%d");

var x = d3.scaleTime()
    .rangeRound([0, width]);

var y = d3.scaleLinear()
    .rangeRound([height, 0])
	// .domain([0, 20]);

var line = d3.line()
    .x(function(d) { return x(d.Time); })
    .y(function(d) { return y(d.Rain); });

d3.csv("Rain.csv", function(d) {
  d.Time = parseTime(d.Time);
  // d.Time = parseTime(d.Time);
  d.Rain = +d.Rain;
  // d = d.filter(function(d)  {
		// return  d.Rain  >  1
		// });
  return d;
}, function(error, data) {
  if (error) throw error;
	data = data.filter(function(data)  {
		return  data.Time  >  (starttime)
		});
	data = data.filter(function(data)  {
	return  data.Time <  (stoptime)
	});
  x.domain(d3.extent(data, function(d) { return d.Time; }));
  y.domain(d3.extent(data, function(d) { return d.Rain; }));
  // console.log(function(data){return data.Time})
  console.log(parseTime("1990-02-28 19:27:59"))
  g.append("g")
      .attr("transform", "translate(0," + height + ")")
      .call(d3.axisBottom(x))
    .select(".domain")
      .remove();

  g.append("g")
      .call(d3.axisLeft(y))
    .append("text")
      .attr("fill", "#000")
      .attr("transform", "rotate(-90)")
      .attr("y", 6)
      .attr("dy", "0.71em")
      .attr("text-anchor", "end")
      .text("Rain intensity [mum/s]");

  g.append("path")
      .datum(data)
      .attr("fill", "none")
      .attr("stroke", "steelblue")
      .attr("stroke-linejoin", "round")
      .attr("stroke-linecap", "round")
      .attr("stroke-width", 1.5)
      .attr("d", line);
});
// d3.select("#start").on("click", function() {
// console.log("click")
	// y.domain([0,30]); // Set New Position
	// });
}
