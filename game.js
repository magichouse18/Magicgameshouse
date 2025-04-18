const config = {
  type: Phaser.AUTO,
  width: 800, height: 600,
  parent: 'game-container',
  backgroundColor: '#110022',       // viola scuro
  physics: { default: 'arcade', arcade: { gravity: { y: 200 } } },
  scene: { preload, create, update }
};
let player, cursors, leaves, bricks, score = 0, scoreText;
new Phaser.Game(config);

function preload() {
  this.load.image('player', 'assets/player.png');
  this.load.image('leaf',   'assets/leaf.png');
  this.load.image('brick',  'assets/brick.png');
}

function create() {
  player = this.physics.add.sprite(400, 550, 'player').setScale(0.5);
  player.setCollideWorldBounds(true);

  leaves = this.physics.add.group();
  bricks = this.physics.add.group();

  scoreText = this.add.text(16,16, 'Score: 0', { fontSize:'32px', fill:'#0f0' });
  cursors = this.input.keyboard.createCursorKeys();

  // Oggetti che cadono ogni secondo
  this.time.addEvent({
    delay: 1000, loop: true,
    callback: () => {
      const x = Phaser.Math.Between(50, 750);
      if (Math.random() < 0.7) leaves.create(x, 0, 'leaf').setVelocityY(200).setScale(0.5);
      else                bricks.create(x, 0, 'brick').setVelocityY(200).setScale(0.5);
    }
  });

  this.physics.add.overlap(player, leaves, (p,l)=>{ l.destroy(); score+=10; scoreText.setText('Score: '+score); }, null, this);
  this.physics.add.overlap(player, bricks, (p,b)=>{ b.destroy(); score+=25; scoreText.setText('Score: '+score); }, null, this);
}

function update() {
  player.setVelocityX(0);
  if (cursors.left.isDown)  player.setVelocityX(-300);
  if (cursors.right.isDown) player.setVelocityX(300);
}
