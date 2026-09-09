const { Resvg } = require('@resvg/resvg-js');
const fs = require('fs');

const svgPath = process.argv[2];
const outPath = process.argv[3];

try {
    const svg = fs.readFileSync(svgPath);
    const resvg = new Resvg(svg, {
        fitTo: {
            mode: 'width',
            value: 1000,
        },
    });
    const pngData = resvg.render();
    const pngBuffer = pngData.asPng();
    fs.writeFileSync(outPath, pngBuffer);
} catch (e) {
    console.error(e);
    process.exit(1);
}
