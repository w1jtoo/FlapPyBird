function displayLeaderBoard() {
    const cont = document.getElementById('container');
    const ol = document.createElement('ol');
    ol.classList.add('list');
    (fetch("http://localhost:8000/score.json").then(function(response) {
        return response.json();
    })).then(function(items) {
        items.sort((a, b) =>  (b.score - a.score)).forEach((item) => {
            const li = document.createElement('li');
            li.classList.add('item');
            const img = document.createElement('img');
            img.src = item.img || './defaultAvatar.svg';
            img.classList.add('ava')
            li.appendChild(img);

            const fio = document.createElement('div');
            fio.innerText = item.name;
            fio.classList.add('fio');
            li.appendChild(fio);

            const score = document.createElement('div');
            score.innerText = item.score;
            score.classList.add('score')
            li.appendChild(score);
            ol.appendChild(li);
        });
        cont.innerHTML = '';
        cont.appendChild(ol);
    });

    setTimeout(displayLeaderBoard, 2000);
};

displayLeaderBoard();