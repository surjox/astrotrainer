
const fs = require("fs");
const path = require("path");
const sharp = require("sharp");

const ROOT = path.join(__dirname, "public", "messier");

async function getImages(dir) {
    let files = [];

    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const fullPath = path.join(dir, entry.name);

        if (entry.isDirectory()) {
            files.push(...await getImages(fullPath));
        } else if (entry.isFile() && /\.webp$/i.test(entry.name)) {
            files.push(fullPath);
        }
    }

    return files;
}

async function main() {
    if (!fs.existsSync(ROOT)) {
        throw new Error(`Directory not found: ${ROOT}`);
    }

    const images = await getImages(ROOT);

    let totalBefore = 0;
    let totalAfter = 0;
    let optimized = 0;
    let unchanged = 0;

    console.log(`Found ${images.length} WebP images.\n`);

    for (const file of images) {
        const originalSize = fs.statSync(file).size;
        const tempFile = file + ".tmp.webp";

        try {
            await sharp(file)
                .webp({
                    lossless: true,
                    effort: 6
                })
                .toFile(tempFile);

            const newSize = fs.statSync(tempFile).size;

            if (newSize < originalSize) {
                fs.renameSync(tempFile, file);
                totalAfter += newSize;
                optimized++;

                console.log(
                    `${path.relative(ROOT, file)}: ` +
                    `${(originalSize / 1024).toFixed(1)} KB → ` +
                    `${(newSize / 1024).toFixed(1)} KB`
                );
            } else {
                fs.unlinkSync(tempFile);
                totalAfter += originalSize;
                unchanged++;

                console.log(
                    `${path.relative(ROOT, file)}: unchanged`
                );
            }

            totalBefore += originalSize;

        } catch (error) {
            if (fs.existsSync(tempFile)) {
                fs.unlinkSync(tempFile);
            }

            totalBefore += originalSize;
            totalAfter += originalSize;

            console.error(`Failed: ${file}`, error.message);
            unchanged++;
        }
    }

    const saved = totalBefore - totalAfter;
    const reduction = totalBefore
        ? (saved / totalBefore) * 100
        : 0;

    console.log("\n========== SUMMARY ==========");
    console.log(`Total images: ${images.length}`);
    console.log(`Optimized: ${optimized}`);
    console.log(`Unchanged/failed: ${unchanged}`);
    console.log(`Original size: ${(totalBefore / 1048576).toFixed(2)} MB`);
    console.log(`Final size: ${(totalAfter / 1048576).toFixed(2)} MB`);
    console.log(`Saved: ${(saved / 1048576).toFixed(2)} MB`);
    console.log(`Reduction: ${reduction.toFixed(2)}%`);
}

main().catch(console.error);
