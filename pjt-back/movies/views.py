from .models import Movie, Review, Recommend, Actor, Director, CommingMovie, Genre, RecommendReview, MovieComment
from .serializers import MovieSerializer, GenreSerializer
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from rest_framework.response import Response
from pprint import pprint
from decouple import config
import requests
import datetime
import bs4



def commingmovieupdate(request):
    URL = config('COMMING_MOVIE_URL')
    
    html = requests.get(URL).text
    comming_dates = bs4.BeautifulSoup(html, 'html.parser')
    comming_dates = comming_dates.select('.lst_wrap')
    today = datetime.date.today()

    for comming_date in comming_dates:
        comming_movies = comming_date.select('li')
        
        for comming_movie in comming_movies:
            post_url = 'img/base_poster.jpg'
            img_tag = comming_movie.select_one('img')
            for string in str(img_tag).split():
                if string[:3] == 'src':
                    post_url = string.split('jpg')[0][5:] + 'jpg'
            
            openDt = ''.join(comming_movie.select_one('.lst_dsc .info_txt1 dd').text.split()[-2].split('.'))
            title = comming_movie.select_one('.tit').a.text
            
            openDt = int(openDt)
            if openDt < 10000000:
                openDt *= 100
                openDt += 1
            openDt = datetime.date(openDt // 10000, openDt // 100 % 100, openDt % 100)
            print(openDt, title)
            temp_comming_movie = CommingMovie()
            temp_comming_movie.title = title
            temp_comming_movie.openDt = openDt
            temp_comming_movie.post_url = post_url
            try:
                temp_comming_movie.save()
            except:
                continue
                


        
    return JsonResponse({'commingMovies': CommingMovie.objects.all().count()})


# @require_POST
def movieupdate(request):
    
    key = config('API_KEY')
    BASE_URL = config('BASE_URL')

    HEADERS = {
        'X-Naver-Client-Id' : config('CLIENT_ID'),
        'X-Naver-Client-Secret' : config('CLIENT_SECRET'),
    }
    NAVER_BASE_URL = config('NAVER_BASE_URL')

    for week_ago in range(130, 200):
        targetDt = datetime.date.today() - datetime.timedelta(weeks=week_ago)
        targetDt = targetDt.strftime('%Y%m%d')
        print(targetDt)
        api_url =f'{BASE_URL}boxoffice/searchWeeklyBoxOfficeList.json?key={key}&targetDt={targetDt}'

        response = requests.get(api_url).json()['boxOfficeResult']['weeklyBoxOfficeList']
        
        for movie in response:
            try:
                movieCd = movie['movieCd']
                if Movie.objects.filter(code=f'{movieCd}'):
                    print('넘어갑니다')
                    continue
                audiAcc = movie['audiAcc']
                
                #영화 상세정보 들어가기
                detail_url = f'{BASE_URL}movie/searchMovieInfo.json?key={key}&movieCd={movieCd}'
                movie_info = requests.get(detail_url).json()['movieInfoResult']['movieInfo']
                movieNm = movie_info['movieNm']
                prdtYear = movie_info['prdtYear']
                genres = movie_info['genres']

                for genre in genres:
                    genreNm = genre['genreNm']
                    temp_genre = Genre()
                    temp_genre.name = genreNm
                    try:
                        temp_genre.save()
                        genre['id'] = temp_genre.id
                    except:
                        temp_genre = get_object_or_404(Genre, name=f'{genreNm}')
                        genre['id'] = temp_genre.id
                        continue

                directors = movie_info['directors']
                actors = movie_info['actors']
                # [{'peopleNm' : '조진웅'}, {}]
                if movie_info['audits']:
                    watchGradeNm = movie_info['audits'][0]['watchGradeNm']
                else:
                    watchGradeNm = ''

                if watchGradeNm == '15세이상관람가':
                    watchgrade = 15
                elif watchGradeNm == '12세이상관람가':
                    watchgrade = 12
                elif watchGradeNm == '중학생이상관람가':
                    watchgrade = 14
                elif watchGradeNm == '청소년관람불가':
                    watchgrade = 20
                elif watchGradeNm == '전체관람가':
                    watchgrade = 0
                else:
                    watchgrade = 0



                #네이버 영화 상세정보 들어가기 -> 네이버 영화 api에서 영화포스터 가져오고, 네이버영화 홈페이지 링크를 갖고오기위하여 필요함.
                naver_url = f'{NAVER_BASE_URL}?query={movieNm}&yearfrom={prdtYear}&yearto={prdtYear}'
                movie_naver_detail = requests.get(naver_url, headers=HEADERS).json()
                if not movie_naver_detail['items']:
                    print('네이버 정보가 없네요 : ', movieNm)
                    continue
                movie_link = movie_naver_detail['items'][0]['link'].replace('basic', 'detail')
                print(movieNm)
                post_url = movie_naver_detail['items'][0]['image']
                userRating = movie_naver_detail['items'][0]['userRating']

                discription_html = requests.get(movie_naver_detail['items'][0]['link']).text
                discription_page = bs4.BeautifulSoup(discription_html, 'html.parser')
                discription = discription_page.select_one(f'p[class="con_tx"]')
                if discription:
                    discription = discription.text
                else:
                    discription = ''
                
                html = requests.get(movie_link+'#tab').text
                naver_movie = bs4.BeautifulSoup(html, 'html.parser')
                
                naver_movie = naver_movie.select_one('.lst_people')
                

                for person in actors + directors:
                    peopleNm = person['peopleNm']
                    img_url = 'img/person_base.jpg'

                    if naver_movie:
                        img_tag = naver_movie.select_one(f'img[alt="{peopleNm}"]')
                        
                        for string in str(img_tag).split():
                            if string[:3] == 'src':
                                img_url = string.split('jpg')[0][5:] + 'jpg'

                    person_detail_url = f'{BASE_URL}/people/searchPeopleList.json?key={key}&peopleNm={peopleNm}&filmoNames={movieNm}'
                    people_list = requests.get(person_detail_url).json()['peopleListResult']
                    if not people_list:
                        print('이사람 없어요 : ', peopleNm)
                    person_detail = people_list['peopleList'][0]

                    peopleCd = person_detail['peopleCd']
                    if person in actors:
                        temp_person = Actor()
                    else:
                        temp_person = Director()
                    temp_person.name = peopleNm
                    temp_person.code = peopleCd
                    temp_person.image_url = img_url
                    try:
                        temp_person.save()
                    except:
                        if person in actors:
                            target_person = get_object_or_404(Actor, code=peopleCd)
                        else:
                            target_person = get_object_or_404(Director, code=peopleCd)
                        person['id'] = target_person.id
                        continue
                    person['id'] = temp_person.id

                temp_movie = Movie()
                temp_movie.title = movieNm
                temp_movie.code = movieCd
                temp_movie.audience = audiAcc
                temp_movie.post_url = post_url
                temp_movie.score = float(userRating)
                temp_movie.watch_grade = watchgrade
                temp_movie.watch_grade_name = watchGradeNm
                temp_movie.discription = discription
                try:
                    temp_movie.save()
                except:
                    temp_movie = get_object_or_404(Movie, code = movieCd)
                    if int(temp_movie.audience) < int(audiAcc):
                        temp_movie.audience = audiAcc
                        temp_movie.save()
                    
                for actor in actors:
                    target_actor = get_object_or_404(Actor, pk=actor['id'])
                    temp_movie.actors.add(target_actor)
                
                for director in directors:
                    target_director = get_object_or_404(Director, pk=director['id'])
                    temp_movie.directors.add(target_director)
                
                for genre in genres:
                    target_genre = get_object_or_404(Genre, pk=genre['id'])
                    temp_movie.genres.add(target_genre)
            except:
                continue


    movies = Movie.objects.all()
    context = {
        'movies': movies.count()
    }
    return JsonResponse(context)

def homemovielist(request, genre_id):
    
    genre = get_object_or_404(Genre, pk=genre_id)
    serializer = GenreSerializer(instance=genre)
    pprint(serializer.data)
    return JsonResponse(serializer.data)

def searchMovie(request, movie_nm):
    if movie_nm == ' ':
        return JsonResponse({'movies': []})
    
    movies = Movie.objects.filter(title__icontains=movie_nm)
    
    serializer = MovieSerializer(instance=movies, many=True)

    return JsonResponse({'movies': serializer.data})
