const html = document.documentElement.innerHTML;\r\n\r\nconst matches = html.match(\/\"@type\"\\s*:\\s*\"?Organization\"?\/gi);\r\n\r\nreturn seoSpider.data(matches ? matches.length : 0);
