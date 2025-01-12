const script = document.createElement("script");

script.src = "https://kit.fontawesome.com/49044c05b2.js";
script.crossorigin="anonymous"

document.body.appendChild(script);

let isHovering = false;

const banner = document.getElementById('book-banner');

banner.addEventListener('mouseenter', function() {
    isHovering = true;
});

banner.addEventListener('mouseleave', function() {
    isHovering = false;
});

let start = new Date().getTime();

const originPosition = { x: 0, y: 0 };

const last = {
  starTimestamp: start,
  starPosition: originPosition,
  mousePosition: originPosition
}

const config = {
  minimumTimeBetweenStars: 200,
  minimumDistanceBetweenStars: 100,
  colors: ["159, 81, 178", "59, 54, 178", "231, 233, 235"],
  sizes: ["1.4rem", "1rem", "0.6rem"],
}

let count = 0;
  
const rand = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min
const selectRandom = items => items[rand(0, items.length - 1)];

const withUnit = (value, unit) => `${value}${unit}`,
      px = value => withUnit(value, "px"),
      ms = value => withUnit(value, "ms");

const calcDistance = (a, b) => {
  const diffX = b.x - a.x,
        diffY = b.y - a.y;
  
  return Math.sqrt(Math.pow(diffX, 2) + Math.pow(diffY, 2));
}

const calcElapsedTime = (start, end) => end - start;

const appendElement = element => banner.appendChild(element)

const removeElement = (element, delay) => setTimeout(() => banner.removeChild(element), delay);

const createStar = position => {
  const star = document.createElement("span"),
        color = selectRandom(config.colors);
  
  
  star.className = "fa-solid fa-star star";
  
  star.style.left = px(position.x);
  star.style.top = px(position.y);
  star.style.fontSize = selectRandom(config.sizes);
  star.style.color = `rgb(${color})`;
  star.style.textShadow = `0px 0px 1.5rem rgb(${color} / 0.5)`;
  
  appendElement(star);

  removeElement(star, 3000);
}

const updateLastStar = position => {
  last.starTimestamp = new Date().getTime();

  last.starPosition = position;
}

const updateLastMousePosition = position => last.mousePosition = position;

const adjustLastMousePosition = position => {
  if(last.mousePosition.x === 0 && last.mousePosition.y === 0) {
    last.mousePosition = position;
  }
};

const handleOnMove = e => {
  if (isHovering) {
    const mousePosition = { x: e.clientX, y: e.clientY }
  
    adjustLastMousePosition(mousePosition);
  
    const now = new Date().getTime();
    const hasMovedFarEnough = calcDistance(last.starPosition, mousePosition) >= config.minimumDistanceBetweenStars;
    const hasBeenLongEnough = calcElapsedTime(last.starTimestamp, now) > config.minimumTimeBetweenStars;
  
    if(hasMovedFarEnough || hasBeenLongEnough) {
      createStar(mousePosition);
    
      updateLastStar(mousePosition);
    }
  
    updateLastMousePosition(mousePosition);
  } 
  
}

window.onmousemove = e => handleOnMove(e);

window.ontouchmove = e => handleOnMove(e.touches[0]);

document.body.onmouseleave = () => updateLastMousePosition(originPosition);