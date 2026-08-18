const questions = [...document.querySelectorAll(\'h1,h2,h3,h4,h5,h6,p,strong\')]\r\n    .filter(el => el.innerText.trim().endsWith(\'?\'));\r\n\r\nreturn seoSpider.data(questions.length);
