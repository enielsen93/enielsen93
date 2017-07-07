width = 960,
    height = 136,
    cellSize = 17;

var formatPercent = d3.format(".1%");

var color = d3.scaleQuantize()
	.domain([0.1, 40])
	.range(["#FFFFFF", "#E7E5F7", "#D0CCEF", "#B9B3E7", "#A199DF", "#8A80D8", "#7367D0", "#5B4DC8", "#4434C0", "#2D1BB8", "#1602B1"]);

var parseTimeInput = d3.timeParse("%Y-%m-%d");	
	
var svg = d3.select("#calid")
  .data(d3.range(1990, 2017))
  .enter().append("svg")
    .attr("width", width)
    .attr("height", height)
  .append("g")
    .attr("transform", "translate(" + ((width - cellSize * 53) / 2) + "," + (height - cellSize * 7 - 1) + ")");

svg.append("text")
    .attr("transform", "translate(-6," + cellSize * 3.5 + ")rotate(-90)")
    .attr("font-family", "sans-serif")
    .attr("font-size", 10)
    .attr("text-anchor", "middle")
    .text(function(d) { return d; });

var rect = svg.append("g")
    .attr("fill", "none")
    .attr("stroke", "#ccc")
  .selectAll("rect")
  .data(function(d) { return d3.timeDays(new Date(d, 0, 1), new Date(d + 1, 0, 1)); })
  .enter().append("rect")
    .attr("width", cellSize)
    .attr("height", cellSize)
    .attr("x", function(d) { return d3.timeWeek.count(d3.timeYear(d), d) * cellSize; })
    .attr("y", function(d) { return d.getDay() * cellSize; })
    .datum(d3.timeFormat("%Y-%m-%d"))
	

svg.append("g")
    .attr("fill", "none")
    .attr("stroke", "#000")
  .selectAll("path")
  .on("mouseout", function(){
      console.log("clicked!");
    })
  .data(function(d) { return d3.timeMonths(new Date(d, 0, 1), new Date(d + 1, 0, 1)); })
  .enter().append("path")
    .attr("d", pathMonth);

d3.csv("RainStats.csv", function(error, csv) {
  var data = d3.nest()
      .key(function(d) { return d.Date; })
      .rollup(function(d) { return (d[0].agg0 )})
    .object(csv);

  rect.filter(function(d) { return d in data; })
      .attr("fill", function(d) { return color(data[d]); })
	  .on("click", function(d){
		  drawplotid(parseTimeInput(d),d3.timeDay.offset(parseTimeInput(d),1));
		  console.log(d);})
    .append("title")
      .text(function(d) { return d + ": " + (data[d]); });
});

function pathMonth(t0) {
  var t1 = new Date(t0.getFullYear(), t0.getMonth() + 1, 0),
      d0 = t0.getDay(), w0 = d3.timeWeek.count(d3.timeYear(t0), t0),
      d1 = t1.getDay(), w1 = d3.timeWeek.count(d3.timeYear(t1), t1);
  return "M" + (w0 + 1) * cellSize + "," + d0 * cellSize
      + "H" + w0 * cellSize + "V" + 7 * cellSize
      + "H" + w1 * cellSize + "V" + (d1 + 1) * cellSize
      + "H" + (w1 + 1) * cellSize + "V" + 0
      + "H" + (w0 + 1) * cellSize + "Z";
}